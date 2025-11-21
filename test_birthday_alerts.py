#!/usr/bin/env python3
"""
Test Birthday Alerts - Set up test birthdays for demonstration
This script updates existing employee DOB fields for testing the birthday alert feature
"""

import sqlite3
from datetime import datetime, timedelta

def setup_test_birthdays():
    """Set up test birthdays to demonstrate the alert feature"""
    
    print("=" * 80)
    print("🎂 Setting Up Test Birthdays for Demonstration")
    print("=" * 80)
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Get current date
    today = datetime.now()
    
    # Create test dates:
    # - Birthday in 2 days (will show alert)
    # - Birthday tomorrow (will show alert)
    # - Birthday today (will show "Today is birthday!" alert)
    
    two_days_later = today + timedelta(days=2)
    tomorrow = today + timedelta(days=1)
    
    print(f"\n📅 Today's date: {today.strftime('%d %B %Y')}")
    print(f"\n📝 Creating test birthdays:")
    print(f"   ✨ 2 days from now: {two_days_later.strftime('%d %B')} (will show alert)")
    print(f"   ✨ Tomorrow: {tomorrow.strftime('%d %B')} (will show alert)")
    print(f"   ✨ Today: {today.strftime('%d %B')} (will show 'Today is birthday!' alert)")
    
    # Get first 3 employees
    cursor.execute("""
        SELECT ei.id, ei.full_name, ei.email 
        FROM employee_info ei 
        LIMIT 3
    """)
    employees = cursor.fetchall()
    
    if len(employees) < 1:
        print("\n⚠️  No employees found in the database!")
        print("   Please add employee information first through the ERP system.")
        conn.close()
        return False
    
    print(f"\n🔄 Updating {len(employees)} employee(s) with test birthdays...\n")
    
    # Test dates in YYYY-MM-DD format
    test_dates = [
        f"{two_days_later.year}-{two_days_later.month:02d}-{two_days_later.day:02d}",
        f"{tomorrow.year}-{tomorrow.month:02d}-{tomorrow.day:02d}",
        f"{today.year}-{today.month:02d}-{today.day:02d}"
    ]
    
    for i, emp in enumerate(employees):
        emp_id, name, email = emp
        if i < len(test_dates):
            birthday = test_dates[i]
            cursor.execute("UPDATE employee_info SET dob = ? WHERE id = ?", (birthday, emp_id))
            
            # Display which date this employee got
            if i == 0:
                print(f"   ✅ {name}: {birthday} (Birthday in 2 days)")
            elif i == 1:
                print(f"   ✅ {name}: {birthday} (Birthday tomorrow)")
            else:
                print(f"   ✅ {name}: {birthday} (Birthday TODAY! 🎉)")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ Test birthdays set up successfully!")
    print("\n💡 Next steps:")
    print("   1. Open your ERP dashboard (either as Admin or regular user)")
    print("   2. You should see a colorful birthday alert modal popup!")
    print("   3. The alerts will show based on the test dates set above")
    print("\n📝 Note: The birthday alerts check the 'dob' field in EmployeeInfo")
    print("=" * 80)
    
    return True

def list_current_birthdays():
    """List all employees and their birthdays"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT full_name, email, dob 
        FROM employee_info 
        WHERE dob IS NOT NULL
        ORDER BY full_name
    """)
    employees = cursor.fetchall()
    
    print("\n📋 Current Employee Birthdays:")
    print("=" * 80)
    
    if not employees:
        print("   No birthdays set in the system.")
    else:
        print(f"{'Name':<30} {'Email':<35} {'DOB':<15}")
        print("-" * 80)
        for emp in employees:
            name, email, dob = emp
            print(f"{name:<30} {email:<35} {dob:<15}")
    
    print("=" * 80)
    conn.close()

if __name__ == "__main__":
    print("\n🎉 Birthday Alerts Test Utility\n")
    print("This script will set up test birthdays for the first 3 employees")
    print("in your database to demonstrate the birthday alert feature.\n")
    
    choice = input("Do you want to:\n1. Set up test birthdays\n2. List current birthdays\n\nEnter choice (1 or 2): ").strip()
    
    if choice == '1':
        confirm = input("\n⚠️  This will modify DOB for up to 3 employees. Continue? (y/n): ").strip().lower()
        if confirm == 'y':
            setup_test_birthdays()
    elif choice == '2':
        list_current_birthdays()
    else:
        print("Invalid choice!")


