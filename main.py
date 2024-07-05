import sqlite3
import getpass
from datetime import datetime, timedelta

# Connect to the SQLite database
path = input("Enter path to Database:")
db_path = path
conn = sqlite3.connect(db_path)
cursor = conn.cursor()


#LOGIN SCREEN(#0)
def login(email):
    if not validate_email(email):
        # email needs to be in a valid email format
        return "Invalid email"
    cursor.execute(f"SELECT email FROM members WHERE UPPER(email) = '{email.upper()}'")
    members = cursor.fetchall()
    if members != []:  # returning member
        pw_fail = True
        while pw_fail:
            password = getpass.getpass()
            cursor.execute(f"SELECT name FROM members WHERE UPPER(email) = '{email.upper()}' AND passwd = '{password}'")
            names = cursor.fetchone()
            if names != None:  # correct password
                pw_fail = False
                print(f"Welcome back {names[0]}!")
            else:  # incorrect password
                print("Incorrect password, ", end = '')
    else:  # new member
        password = input("Create a password: ")
        name = input("Enter a name: ")
        byear = input("Enter a birth year: ")
        faculty = input("Enter your faculty name: ")
        cursor.execute(f"INSERT INTO members values('{email}', '{password}', '{name}', {byear}, '{faculty}');")
        conn.commit()
        print(f"Welcome to the database {name}!")
    return email


def validate_email(email):
    if '@' not in email:  # email needs to have @ in it
        return False
    if '.' not in email[email.find('@'):]:  # email needs a . in it
        return False
    if email.find('.') - email.find('@') <= 1:  # e.g. email@.ca
        return False
    if email.find('.') == len(email)-1:  # e.g. email@domain.
        return False
    return True  # email is valid


#MEMBER PROFILE (#1)
def view_personal_info(email):
    cursor.execute("SELECT name, email, byear FROM members WHERE UPPER(email) = ?", (email.upper(),))
    info = cursor.fetchone()

    if info:
        print(f'Name: {info[0]}\nEmail: {info[1]}\nBirth Year: {info[2]}')
    else:
        print("Member not found.")
    
    return

def view_borrowings(email):
    # Previous Borrowings
    cursor.execute("SELECT COUNT(*) FROM borrowings WHERE member = ? AND end_date IS NOT NULL", (email,))
    previous_borrowings = cursor.fetchone()[0]

    # Current Borrowings 
    cursor.execute("SELECT COUNT(*) FROM borrowings WHERE member = ? AND end_date IS NULL", (email,))
    current_borrowings = cursor.fetchone()[0]

    # Overdue Borrowings
    cursor.execute("SELECT COUNT(*) FROM borrowings WHERE member = ? AND end_date IS NULL AND start_date < date('now', '-20 day')", (email,))
    overdue_borrowings = cursor.fetchone()[0]

    print(f'Previous Borrowings: {previous_borrowings}\nCurrent Borrowings: {current_borrowings}\nOverdue Borrowings: {overdue_borrowings}')

    return

def view_penalties(email): 
    cursor.execute("SELECT COUNT(*), SUM(amount - IFNULL(paid_amount, 0)) FROM penalties JOIN borrowings ON penalties.bid = borrowings.bid WHERE borrowings.member = ? AND (paid_amount < amount OR paid_amount IS NULL)", (email,))
    penalties_info = cursor.fetchone()
    unpaid_penalties, total_debt = penalties_info
    print(f'Unpaid Penalties: {unpaid_penalties}\nTotal Debt: {total_debt}')

def member_menu(email):
    while True:
        print("\n1. View Personal Info\n2. View Borrowings\n3. View Penalties\n4. Exit")
        choice = int(input("Please choose an option: "))
        if choice == 1:
            view_personal_info(email)
        elif choice == 2:
            view_borrowings(email)
        elif choice == 3:
            view_penalties(email)
        elif choice == 4:
            break
        else:
            print("Invalid choice. Please try again.")


#####

#RETURNING A BOOK (#2)
def user_borrowings(user_name):
    query = """
    SELECT b.bid, bk.title, b.start_date, DATE(b.start_date, '+20 days') AS return_deadline
    FROM borrowings b
    JOIN books bk ON b.book_id = bk.book_id
    JOIN members m ON b.member = m.email
    WHERE UPPER(m.email) = ? AND (b.end_date IS NULL) 
    """
    cursor.execute(query, (user_name.upper(),)) #OR b.end_date > return_deadline
    return cursor.fetchall()

def display_borrowings(borrowings):
    print("Your current borrowings:")
    for borrowing in borrowings:
        print(f"Borrowing ID: {borrowing[0]}, Book Title: {borrowing[1]}, Borrowing Date: {borrowing[2]}, Return Deadline: {borrowing[3]}")


def return_book(borrowing_id):
    returning_date = datetime.now().strftime('%Y-%m-%d')
    query = "UPDATE borrowings SET end_date = ? WHERE bid = ?"
    cursor.execute(query, (returning_date, borrowing_id))
    conn.commit()
    print(f"Book with Borrowing ID {borrowing_id} returned successfully on {returning_date}")
    query1 = "SELECT start_date, end_date FROM borrowings WHERE bid = ?"
    cursor.execute(query1, (borrowing_id,))
    result = cursor.fetchone()

    if result:
        start_date = datetime.strptime(result[0], '%Y-%m-%d')
        end_date = datetime.strptime(result[1], '%Y-%m-%d')
        deadline = start_date + timedelta(days=20)
        if end_date > deadline:
            days_delayed = (end_date - deadline).days
            penalty = days_delayed * 1
            print(f"Penalty applied: ${penalty}")
            new_pid =  cursor.execute("SELECT MAX(pid) FROM penalties").fetchone()[0] + 1
            insert_query = "INSERT INTO penalties (pid, bid, amount, paid_amount) VALUES (?,?, ?, ?)"
            paid = None
            cursor.execute(insert_query, (new_pid, borrowing_id, penalty, paid))

    conn.commit()
    print(f"Book with Borrowing ID {borrowing_id} returned successfully on {returning_date}")

def write_review(borrowing_id, member):
    review_text = input("Enter your review for the book: ")
    while True:
        rating = input("Enter your rating for the book (1-5): ")
        if rating.isdigit() and 1 <= int(rating) <= 5:
            break
        else:
            print("Invalid rating. Please enter a number between 1 and 5.")
    review_date = datetime.now().strftime('%Y-%m-%d')
    review_id = cursor.execute("SELECT MAX(rid) FROM reviews").fetchone()[0] + 1
    book_id_cur = cursor.execute("SELECT book_id FROM borrowings WHERE bid = ?",(borrowing_id,))
    book_id = book_id_cur.fetchone()[0]
    cursor.execute("INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?)", (review_id, book_id, member, rating, review_text, review_date))
    conn.commit()
    print("Review submitted successfully.")
def return_main(user_name):
    borrowings = user_borrowings(user_name)

    if not borrowings:
        print("You have no current borrowings.")
    else:
        # Display the user's current borrowings
        display_borrowings(borrowings)

        # Ask the user to select a borrowing to return
        bid = int(input("Enter the Borrowing ID of the book you want to return (0 to exit): "))

        if bid != 0:
            # Return the selected book
            return_book(bid)
            # Ask if the user wants to write a review
            write_review_choice = input("Would you like to write a review for this book? (yes/no): ")
            if write_review_choice.lower() == 'yes':
                write_review(bid, user_name)
    return
    
#####
#SEARCH FOR BOOKS(#3)
def search_books(keyword, email):
    cursor.execute(f"""
        SELECT books.book_id, title, author, pyear
        FROM books
        WHERE UPPER(title) LIKE '%{keyword.upper()}%'
        ORDER BY title                
""")
    books = cursor.fetchall()
    cursor.execute(f"""
        SELECT book_id, title, author, pyear
        FROM books b
        WHERE UPPER(author) LIKE '%{keyword.upper()}%'
        ORDER BY author              
""")
    authors = cursor.fetchall()
    books = books + authors
    if books != []:  # there was books found with the keyword
        for i in range(len(books)):
            books[i] = list(books[i])
            avg_ratings(books[i])
            is_borrowable(books[i])
            books[i] = tuple(books[i])
            print(f'Book ID: {books[i][0]:<6} | Title: {books[i][1]:<25} | Author: {books[i][2]:<10} | PYear: {books[i][3] if books[i][3] is not None else "":<6} | Average_Rating: {books[i][4] if books[i][4] is not None else "":<10} | Borrowable: {books[i][5]}')
        book_borrowing(books, email)
    else:  # no books found with the keyword
        print("No books found.")


def is_borrowable(book):
    cursor.execute(f"""
            SELECT borrowings.bid
            FROM books, borrowings
            WHERE borrowings.book_id = {book[0]} AND end_date IS NULL
""")
    borrowable = cursor.fetchall()
    if borrowable == []:  # book is not borrowed
        book.append('Available')
    else:  # book is borrowed
        book.append('Borrowed')

def avg_ratings(book):
    cursor.execute(f"""
        SELECT AVG(rating)
        FROM books, reviews
        WHERE reviews.book_id = {book[0]}          
""")
    rating = cursor.fetchone()
    book.append(rating[0])


def book_borrowing(query_result, email):
    not_borrowed = True
    while not_borrowed:
        bid = int(input("Enter the ID of the book you want to borrow (-1 to exit): ")) 
        for row in query_result:
            if row[0] == bid:
                if row[5] == 'Borrowed': 
                    print("Sorry, this book is not available.")
                else:
                    # Borrow the book
                    book_id = bid
                    member = email
                    borrowing_id = cursor.execute("SELECT MAX(bid) FROM borrowings").fetchone()[0] + 1
                    start_date = datetime.today().strftime('%Y-%m-%d')
                    cursor.execute("INSERT INTO borrowings VALUES (?, ?, ?, ?, NULL)", (borrowing_id, member, book_id, start_date))
                    conn.commit()
                    not_borrowed = False
                    print("You have successfully borrowed the book!")
            elif bid == -1: #CHANGES
                return
#####

#PAY A PENALTY (#4)
def unpaid_penalties(user):
    cursor.execute( f"""SELECT borrowings.member, pid, ifnull(amount - ifnull(paid_amount,0), 0), amount
				FROM borrowings
					LEFT JOIN penalties p
    					ON borrowings.bid = p.bid
     				GROUP BY p.pid
					HAVING member = '{user}' AND (ifnull(paid_amount,0) < amount)""")
    members = cursor.fetchall()
    if members == []:  # no unpaid penalties
        print("No penalties to be paid.")
    else:  # unpaid penalties
        print("Penalties to be paid:")
        for i in range(len(members)):
            print(f"{i + 1}. ${members[i][2]}")  # balance due at index 2
        user_input = input("Select penalty to pay or enter any key to skip: ")
        if user_input.isdigit():
            if int(user_input)-1 in range(len(members)):
                cursor.execute(f"""UPDATE penalties
                               SET paid_amount = {members[int(user_input)-1][3]}
                               WHERE pid = {members[int(user_input)-1][1]}""")
                print("Penalty paid.")


def main():
    while True:
        user_email = "Invalid email"
        while user_email == "Invalid email":
            email = input("Please enter your email: ")
            if email == '':
                    break
            user_email = login(email)
        while True:
            menu = int(input("Enter 1 to view Member Profile\nEnter 2 to Return a Book\nEnter 3 to Search for books\nEnter 4 to Pay a Penalty\nEnter 5 to log out\n"))
            if menu == 1:
                member_menu(email)
            elif menu == 2:
                return_main(email)
            elif menu == 3:
                keyword = input("Enter a keyword to search: ")
                search_books(keyword,email)
            elif menu == 4:
                unpaid_penalties(email)
            else:
                print("Goodbye,Have a good day!")
                exit()
main()