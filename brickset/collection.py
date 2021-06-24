from data import DATABASE_FILE, TABLES, BASE_URL
import sqlite3
import jinja2
import requests
import gzip
import io
import csv
from pathlib import Path

schema_template_loader = jinja2.FileSystemLoader('data/templates/schema')
schema_template_env = jinja2.Environment(loader=schema_template_loader)
data_access_template_loader = jinja2.FileSystemLoader('data/templates')
data_access_template_env = jinja2.Environment(loader=data_access_template_loader)


class Collection(object):
    def __init__(self, api_key, username, password, refresh_data=False):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.token = self.login()

        file = Path(DATABASE_FILE)
        if refresh_data or not file.exists():
            print("\n!!! Building inventory database. "
                  "This happens on your first execution or if you explicitly ask to rebuild the "
                  "inventory database !!!\n")
            self.con = sqlite3.connect(DATABASE_FILE)
            self.create_all_tables()
            self.load_all_tables()
        else:
            self.con = sqlite3.connect(DATABASE_FILE)

        self.my_owned_sets = []
        self.set_my_owned_sets()

        self.my_owned_parts_by_color = []
        self.set_owned_parts_by_color()

        self.my_owned_parts = []
        self.set_owned_parts()

    def login(self) -> str:
        response = requests.get(
            'https://brickset.com/api/v3.asmx/login',
            params={'username': self.username, 'password': self.password, 'apiKey': self.api_key}
        )
        response = response.json()
        if response['status'] == "success":
            return response['hash']
        else:
            raise Exception("Login failed: " + response['message'])

    def get_database_connection(self) -> sqlite3.Connection:
        return self.con

    def create_all_tables(self, fail_if_exists=False):
        for table_name in TABLES:
            self.create_table(table_name, fail_if_exists)

    def create_table(self, table_name: str, fail_if_exists=False):
        ddl_template = schema_template_env.get_template(f"{table_name}.sql")
        cur = self.get_database_connection().cursor()
        cur.execute(f"SELECT count(1) FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        (number_of_rows,) = cur.fetchone()
        if number_of_rows > 0 and fail_if_exists:
            raise Exception(f"Tried to create table which already exists: {table_name}")
        if number_of_rows > 0 and not fail_if_exists:
            cur.execute(f"DROP TABLE '{table_name}'")
        cur.execute(ddl_template.render())

    def load_all_tables(self):
        for table_name in TABLES:
            print(f"Loading table {table_name}...")
            self.load_table(table_name)

    def load_table(self, table_name: str):
        web_response = requests.get(f"{BASE_URL}/{table_name}.csv.gz", timeout=30, stream=True)
        csv_gz_file = web_response.content
        f = io.BytesIO(csv_gz_file)
        with gzip.GzipFile(fileobj=f) as fh:
            r = csv.reader(io.TextIOWrapper(fh, 'utf8'))
            i = 0
            con = self.get_database_connection()
            cur = con.cursor()
            for row in r:
                if i == 0:
                    column_names = row
                    literals = ""
                    for column_name in column_names:
                        literals = literals + "?,"
                    literals = literals[:-1]
                    i = 1
                else:
                    row_values = ','.join(f"'{w}'" for w in row)
                    stmt = f"INSERT INTO {table_name} ({','.join(column_names)}) " \
                           f"VALUES ({literals});"
                    try:
                        cur.execute(stmt, row)
                    except:
                        print(f"Could not load row: {row_values}")
        con.commit()

    def get_parts_by_color_for_sets(self, sets) -> dict:
        """
        Returns a dictionary with parts, colors and quantities structured like:
        {
            part_id: {
                name: Part Name,
                color_id1: {
                    name: Color Name,
                    quantity: Quantity of part/color
                },
                color_id2: {
                    name: Color Name,
                    quantity: Quantity of part/color
                },
            }
        }
        :param sets:
        :return:
        """
        result = {}
        sets_in_clause = ""
        for lego_set in sets:
            sets_in_clause = sets_in_clause + f"'{lego_set}',"
        sets_in_clause = sets_in_clause[:-1]
        get_data_template = data_access_template_env.get_template("get_collection_parts_by_color.sql")
        cur = self.get_database_connection().cursor()
        results = cur.execute(get_data_template.render(set_num=sets_in_clause))
        for row in results:
            (part_number, part_name, color_id, color_name, quantity) = row
            if part_number in result:
                result[part_number][color_id] = {'name': color_name, 'quantity': quantity}
            else:
                result[part_number] = {'name': part_name, color_id: {'name': color_name, 'quantity': quantity}}
        return result

    def get_parts_for_sets(self, sets) -> dict:
        """
        Returns a dictionary with parts and quantities structured like:
        {
            part_id1: {
                name: Part Name,
                quantity: Quantity of part/color
            },
            part_id2: {
                name: Part Name,
                quantity: Quantity of part/color
            }
        }
        :param sets:
        :return:
        """
        result = {}
        sets_in_clause = ""
        for lego_set in sets:
            sets_in_clause = sets_in_clause + f"'{lego_set}',"
        sets_in_clause = sets_in_clause[:-1]
        get_data_template = data_access_template_env.get_template("get_collection_parts.sql")
        cur = self.get_database_connection().cursor()
        results = cur.execute(get_data_template.render(set_num=sets_in_clause))
        for row in results:
            (part_number, part_name, quantity) = row
            result[part_number] = {'name': part_name, 'quantity': quantity}
        return result

    def set_my_owned_sets(self):
        response = requests.get(
            'https://brickset.com/api/v3.asmx/getSets',
            params={'apiKey': self.api_key, 'userHash': self.token, 'params': '{owned: 1}'}
        )
        response = response.json()
        # Here we append "-1" to each set number to match the inventory identifiers
        cleaned_sets = [f"{lego_set['number']}-1" for lego_set in response['sets']]
        self.my_owned_sets = cleaned_sets

    def get_my_owned_sets(self) -> list:
        return self.my_owned_sets

    def set_owned_parts_by_color(self):
        self.my_owned_parts_by_color = self.get_parts_by_color_for_sets(self.get_my_owned_sets())

    def get_owned_parts_by_color(self) -> dict:
        return self.get_my_owned_sets()

    def set_owned_parts(self):
        self.my_owned_parts = self.get_parts_for_sets(self.my_owned_sets)

    def get_owned_parts(self) -> dict:
        return self.my_owned_parts

    def get_sets_completion_by_color(self, min_threshold=1, min_parts=30) -> list:
        result_sets = []
        get_data_template = data_access_template_env.get_template("get_all_sets_parts_by_color.sql")
        cur = self.get_database_connection().cursor()
        results = cur.execute(get_data_template.render())
        (current_set_num, current_set_name, current_set_num_parts, current_set_num_parts_owned) = (999999, "", 0, 0)
        for (set_num, set_name, part_num, color_id, quantity) in results:
            if set_num != current_set_num:
                if current_set_num != 999999\
                        and current_set_num_parts_owned/current_set_num_parts >= min_threshold\
                        and current_set_num_parts >= min_parts\
                        and current_set_num not in self.my_owned_sets:
                    result_sets.append(
                        [current_set_num, current_set_name, current_set_num_parts, current_set_num_parts_owned/current_set_num_parts]
                    )
                current_set_num = set_num
                current_set_name = set_name
                current_set_num_parts = 0
                current_set_num_parts_owned = 0

            current_set_num_parts += quantity
            if part_num in self.my_owned_parts_by_color:
                part = self.my_owned_parts_by_color[part_num]
                if color_id in part:
                    color = part[color_id]
                    owned_quantity = color['quantity']
                    if owned_quantity <= quantity:
                        current_set_num_parts_owned += owned_quantity
                    else:
                        current_set_num_parts_owned += quantity

        if current_set_num_parts_owned/current_set_num_parts >= min_threshold \
                and current_set_num_parts >= min_parts\
                and current_set_num not in self.my_owned_sets:
            result_sets.append([set_num, set_name, current_set_num_parts])

        return result_sets

    def get_sets_completion(self, min_threshold=1, min_parts=30) -> list:
        result_sets = []
        get_data_template = data_access_template_env.get_template("get_all_sets_parts.sql")
        cur = self.get_database_connection().cursor()
        results = cur.execute(get_data_template.render())
        (current_set_num, current_set_name, current_set_num_parts, current_set_num_parts_owned) = (999999, "", 0, 0)
        for (set_num, set_name, part_num, quantity) in results:
            if set_num != current_set_num:
                if current_set_num != 999999\
                        and current_set_num_parts_owned/current_set_num_parts >= min_threshold\
                        and current_set_num_parts >= min_parts\
                        and current_set_num not in self.my_owned_sets:
                    result_sets.append(
                        [current_set_num, current_set_name, current_set_num_parts, current_set_num_parts_owned/current_set_num_parts]
                    )
                current_set_num = set_num
                current_set_name = set_name
                current_set_num_parts = 0
                current_set_num_parts_owned = 0

            current_set_num_parts += quantity
            if part_num in self.my_owned_parts:
                part = self.my_owned_parts[part_num]
                owned_quantity = part['quantity']
                if owned_quantity <= quantity:
                    current_set_num_parts_owned += owned_quantity
                else:
                    current_set_num_parts_owned += quantity

        if current_set_num_parts_owned/current_set_num_parts >= min_threshold \
                and current_set_num_parts >= min_parts\
                and current_set_num not in self.my_owned_sets:
            result_sets.append([set_num, set_name, current_set_num_parts])

        return result_sets
