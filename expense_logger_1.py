
#! BASIC EXPENSE LOGGER
from rich.table import Table
from rich.console import Console

expenses = []

# add expense
def add_expense(amount, category, description) -> None:
    """ 
    Add a new expense to the list.
    
    Args:
        amount (float): The amount of the expense.
        category (str): The category of the expense.
        description (str): A brief description of the expense.
    """
    if amount <= 0 or not isinstance(amount, (int, float)):
        print('Amount must be greater than zero.')
        return
    if category.strip() == '':
        print('Category cannot be empty.')
        return
    if description.strip() == '':
        print('Description cannot be empty.')
        return

    expense = {
        'amount': amount,
        'category': category,
        'description': description
    }

    expenses.append(expense)

    print('Expense added successfully!')
    return

# view expenses
def view_expenses() -> None:
    """
    Returns the list of all recorded expenses.
    
    :return: str: A formatted string of all expenses.
    :rtype: str
    """

    console = Console()
    if not expenses or len(expenses) == 0:
        print('No expenses recorded yet.')
        return
    else:
        # print(f'All Expenses\n-------------')
        table = Table(show_header=True, header_style="bold magenta", title='All Expenses\n')
        table.add_column('ID', style='dim', width=6)
        table.add_column('Amount', justify='left')
        table.add_column('Category', justify='left')
        table.add_column('Description', justify='left')
        for idx, expense in enumerate(expenses, start=1):
            table.add_row(str(idx), f'${expense["amount"]:.2f}', expense['category'], expense['description'])
        console.print(table)
        print('\n')
        return

# view summary
def view_summary():
    """
    Returns a summary of expenses by category.
    """
    total_expenses = sum(expense['amount'] for expense in expenses)
    categories = [expense['category'] for expense in expenses]
    categories_total = {category: 0 for category in set(categories)}
    for expense in expenses:
        categories_total[expense['category']] += expense['amount']
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_section()
    table.title = f'\nExpense Summary\nTotal Spending: ${total_expenses:.2f}\n'
    table.add_column('Category', justify='center')
    table.add_column('Total', justify='center')

    # print(f'Expense Summary\n----------------\n')
    for category, total in categories_total.items():
        table.add_row(category, f'${total:.2f}')
        # print(f'{category}: ${total:.2f}')
    console.print(table)
    print('\n')
    return


if __name__ == '__main__':
    print('Personal Finance Tracker\n======================\n')
    while True:
        print(f"""\nMenu:\n1. Add Expense\n2. View All Expenses\n3. View Summary\n4. Exit\n""")
        choice = input('Enter your choice (1 -4 ):')
        if choice == '4':
            print('Goodbye!\n')
            break
        elif choice == '1':
            try:
                amount = float(input('Enter amount: $'))
                category = input('Enter category: ')
                description = input('Enter description: ')
                add_expense(amount, category, description)
            except ValueError:
                print('Invalid input. Please enter a valid number for amount.\n')
        elif choice == '2':
            view_expenses()
        elif choice == '3':
            view_summary()
        else:
            print('Invalid choice. Please select a valid option (1-4).\n')