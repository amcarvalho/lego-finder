from texttable import Texttable


def pretty_print_list_of_lists(lst) -> Texttable:
    table = Texttable()
    table.set_cols_align(["l", "r", "l", "r"])
    lst.insert(0, ["Set #", "Set Name", "# Parts", "% Owned Parts"])
    table.add_rows(lst)
    return table
