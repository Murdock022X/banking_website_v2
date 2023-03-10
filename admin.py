from models import User, Account, Alerts, Messages, Bank_Settings, \
    Statements, Term_Data, Curr_Term
from app import db
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, flash, \
    request, current_app, url_for
from flask_login import login_required, current_user
from format import format_rates
from fpdf import Template
from pdf import Statement_Maker
from utils import check_access
from forms import BankSettingsForm, SendAlertForm, SendMessageForm

class Admin_Tools():
    """
    Toolbox for admin users, these functions should 
    only be available to admins.
    """    


    def modify_bank_settings(savings_ir = -1.0, savings_min = -1.0, checkings_ir = -1.0, checkings_min = -1.0):
        """Changes necessary bank setting to new setting.

        Args:
            savings_ir (float, optional): Savings interest rate. Defaults to -1.0.
            savings_min (float, optional): Savings minimum balance. Defaults to -1.0.
            checkings_ir (float, optional): Checkings interest rate. Defaults to -1.0.
            checkings_min (float, optional): Checkings minimum balance. Defaults to -1.0.
        """        
        # Retrieve current settings
        settings = Bank_Settings.query.get(1)

        # Update the correct interest rate or minimum balance allowed.
        if settings.savings_ir != -1.0:
            settings.savings_ir = savings_ir
        if settings.savings_min != -1.0:
            settings.savings_min = savings_min
        if settings.checkings_ir != -1.0:
            settings.checkings_ir = checkings_ir
        if settings.checkings_min != -1.0:
            settings.checkings_min = checkings_min

        # Commit To Database
        db.session.commit()


    def commit_all_compound():
        """
        Compounds the value on all accounts.
        """        
        accs = Account.query.all()

        # Add compound interest to account balance for each account.
        for acc in accs:
            acc.bal += acc.bal * acc.ir
        
        # Commit To Database
        db.session.commit()


    def commit_alert(content):
        """
        Commits an alert to the database. (Messages are sent to specific 
        users, alerts are sent to all users.)

        Args:
            content (str): The content to send in the alert.
        """        

        # Get Current Datetime
        dt = datetime.now()
        
        # Create New Alert
        alert = Alerts(date=dt, content=content)

        # Add new alert to database and commit.
        db.session.add(alert)

        db.session.commit()
    

    def commit_message(content, username):
        """Commit a message to the database. (Messages are sent to specific 
        users, alerts are sent to all users.)

        Args:
            content (str): The message content.
            username (str): The username for the user to send to.
        """        
        
        # Get Current Datetime
        dt = datetime.now()

        # Create New Message
        message = Messages(date=dt, username=username, content=content)

        # Add new message to database and commit.
        db.session.add(message)

        db.session.commit()


    def assemble_all_statements():
        """
        Assemble statements for all users.
        """        

        # Get all users
        users = User.query.all()

        # For each user write a statement and send to database.
        for user in users:
            # Initiate a Statement_Maker object for the current user.
            sm = Statement_Maker(user.username)

            # Create an entry in the Statements database with the path to the pdf.
            check_statement = Statements.query.filter_by(username=user.username, date=date.today()).first()

            if not check_statement:
                statement = Statements(username=user.username, date=date.today(), name=sm.state_data.name, path=str(sm.pth))
            
                # Add Statement entry to database and commit.
                db.session.add(statement)

                db.session.commit()

            # Write the pdf to the filepath.
            sm.write()


#
# Function no longer in use.
#     def commit_bal_data(acc_no, date=date.today()):
#         """Commit data on the current balance of this account to database.
#
#         Args:
#             acc_no (int): The account number to commit balance data for.
#             date (date, optional): A date object to store the time for which 
#             this balance was taken. Defaults to date.today().
#         """        
# 
#         # Get the account to commit account balance entry on.
#         acc = Account.query.get(acc_no)
#
#         # Create Daily_Bal object to store current balance.
#         bal_statement = Balance_Data(acc_no=acc_no, date=date, bal=acc.bal)
# 
#         # Add bal_statement to database and commit.
#         db.session.add(bal_statement)
#
#         db.session.commit()


#
# This function is no longer useful.
#     def commit_all_bal_data():
#         """
#         Commit current balance to database.
#         """        
#
#         # Get all accounts
#         accounts = Account.query.all()
# 
#         # Enter daily_bal into database.
#         for account in accounts:
#             Admin_Tools.commit_bal_data(account.acc_no)


    def inc_term():
        """
        Increment current term to next term.
        """        

        # Get the current term and increment.
        term = Curr_Term.query.first()
        term.term += 1

        db.session.commit()

        # Get all accounts
        accs = Account.query.all()

        # Create a new term data entry for all acounts.
        for acc in accs:

            # Create the term data object.
            new_term = Term_Data(acc_no=acc.acc_no, term=term.term, 
                                 start_bal=acc.bal)

            # Add the term data object to session and commit.
            db.session.add(new_term)

            db.session.commit()

#
# Function no longer useful.
#
#     def daily_processes():
#         """
#         These processes should be exexcuted daily.
#         """
#
#         # Commit balances for all accounts.
#         Admin_Tools.commit_all_bal_data()


    def term_processes():
        """
        These processes will be executed each term. Term starts sunday, 1 week long.
        """        

        # Compound all accounts at the end of term.
        Admin_Tools.commit_all_compound()

        # Assemble statements for all users.
        Admin_Tools.assemble_all_statements()

        # Increment the current term.
        Admin_Tools.inc_term()

# Create the admin blueprint to be used for privelged actions.
admin = Blueprint('admin', __name__)


@admin.route('/bank_settings/', methods=['POST', 'GET'])
@login_required
def bank_settings():
    if not check_access(current_user.id, 1):
        return redirect(url_for('main.profile'))
    
    form = BankSettingsForm()

    old_rates = Bank_Settings.query.get(1)

    if form.validate_on_submit():
        change_type = int(form.change_type.data)

        if change_type == 0:
            old_rates.savings_apy = form.new_value.data
        elif change_type == 1:
            old_rates.checkings_apy = form.new_value.data
        elif change_type == 2:
            old_rates.savings_min = form.new_value.data
        elif change_type == 3:
            old_rates.checkings_min = form.new_value.data

        db.session.commit()

        flash('Rates Altered', category='info')

    settings = format_rates(old_rates)

    return render_template('bank_settings.html', form=form, rates=settings)

@admin.route('/send_alert/', methods=['POST', 'GET'])
@login_required
def send_alert():
    if not check_access(current_user.id, 1):
        return redirect(url_for('main.profile'))
    
    form = SendAlertForm()

    if form.validate_on_submit():

        Admin_Tools.commit_alert(content=form.content.data)

        flash('Alert Sent', category='info')
    
    return render_template('send_alert.html', form=form)

@admin.route('/send_message/', methods=['POST', 'GET'])
@login_required
def send_message():
    if not check_access(current_user.id, 1):
        return redirect(url_for('main.profile'))
    
    form = SendMessageForm()

    if form.validate_on_submit():

        Admin_Tools.commit_message(content=form.content.data, username=form.username.data)

        flash('Message Sent', category='info')

    return render_template('send_message.html', form=form)

# @admin.route('/compound/', methods=['POST', 'GET'])
# @login_required
# def compound():
#     if not check_access(current_user.id, 1):
#         return redirect('profile.html')
#    
#     if request.method == 'POST':
#         Admin_Tools.commit_compound()
# 
#     return render_template('compound.html')

# @admin.route('/get_statements/', methods=['POST', 'GET'])
# @login_required
# def make_statements():
#     if current_user.id != 1:
#         flash('Only Admins Can Access That Page')
#         return redirect('profile.html')
#     
#     if request.method == 'POST':
#         Admin_Tools.assemble_all_statements()
# 
#     return render_template('make_statements.html')