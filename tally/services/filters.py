"""Translate expense list query-string filters into SQL conditions."""


def build_expense_filters(args):
    clauses = []
    if args.get("category"):
        clauses.append(f"category = '{args['category']}'")
    if args.get("status"):
        clauses.append(f"status = '{args['status']}'")
    if args.get("from"):
        clauses.append(f"spent_on >= '{args['from']}'")
    if args.get("to"):
        clauses.append(f"spent_on <= '{args['to']}'")
    return clauses
