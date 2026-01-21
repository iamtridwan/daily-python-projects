from rich.console import Console
from rich.table import Table


"""
TODO:
 - Uses an Expense class to represent individual expenses
 - Uses an ExpenseTracker class to manage all expenses
 - Stores expense data as object attributes
 - Implements methods for adding, viewing and analyzing expenses
 - Maintains the same functionality as Day 1 but with better structure
 - Demonstrate how classes encapsulate data and behavior together
"""



class Expense:
    def __init__(self, amount: float, category: str, description: str):
        self.amount = amount
        self.category = category
        self.description = description

    def __str__(self):
        return f'${self.amount:.2f} | {self.category} | {self.description}'
    


class ExpenseTracker:
    def __init__(self):
        self.expenses = []

    # add expense
    def add_expense(self, amount:float, category: str, description:str):
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

        expense = Expense(amount, category, description)
        self.expenses.append(expense)

        print('Expense added successfully!')
        return
    
    # view expenses
    def view_expenses(self):
        """
        Returns the list of all recorded expenses.
        
        :return: str: A formatted string of all expenses.
        :rtype: str
        """

        console = Console()
        if not self.expenses or len(self.expenses) == 0:
            print('No expenses recorded yet.')
            return
        else:
            table = Table(show_header=True, header_style="bold magenta", title='All Expenses\n')
            table.add_column('ID', style='dim', width=6)
            table.add_column('Amount', justify='left')
            table.add_column('Category', justify='left')
            table.add_column('Description', justify='left')
            for idx, expense in enumerate(self.expenses, start=1):
                table.add_row(str(idx), f'${expense.amount:.2f}', expense.category, expense.description)
            console.print(table)
            print('\n')
            return
        
    # view summary
    def view_summary(self):
        """
        Provides a summary of expenses by category.
        """
        if not self.expenses or len(self.expenses) == 0:
            print('No expenses recorded yet.')
            return
        
        summary = {}
        total_expenses = sum(expense.amount for expense in self.expenses)
        for expense in self.expenses:
            if expense.category in summary:
                summary[expense.category] += expense.amount
            else:
                summary[expense.category] = expense.amount
        
        console = Console()
        table = Table(show_header=True, header_style="bold magenta", title=f'\nExpense Summary\n\nTotal Spending: ${total_expenses:.2f}\n')
        table.add_column('Category', justify='left')
        table.add_column('Total Amount', justify='left')
        
        for category, total in summary.items():
            table.add_row(category, f'${total:.2f}')
        
        console.print(table)
        print('\n')
        return
    

if __name__ == '__main__':
    print('Personal Finance Tracker\n======================\n')
    tracker = ExpenseTracker()
    while True:
        print(f'\nMenu:\n1. Add Expense\n2. View All Expenses\n3. View Summary\n4. Exit\n')
        choice = input('Enter your choice (1 - 4):')
        if choice == '4':
            print('Goodbye!\n')
            break
        elif choice == '1':
            try:
                amount = float(input('Enter expense amount: $'))
                category = input('Enter category: ')
                description = input('Enter description: ')
                tracker.add_expense(amount, category, description)
            except ValueError:
                print('Invalid amount. Please enter a valid number for amount.\n')
        elif choice == '2':
            tracker.view_expenses()
        elif choice == '3':
            tracker.view_summary()
        else:
            print('Invalid choice. Please enter a valid option (1 - 4).\n')
