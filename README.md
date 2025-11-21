# 🏢 ERP Web Portal

A comprehensive Enterprise Resource Planning (ERP) web application built with Flask and Firebase, designed to manage employee operations, project management, leave requests, asset management, and more.

## ✨ Features

### 🔐 User Management
- **Multi-role Authentication System**: Support for Managing Director, Team Lead, HR, Accounts, and Employee roles
- **User Registration & Login**: Secure authentication with password hashing
- **Role-based Access Control**: Granular permissions for different user roles
- **User Profile Management**: Employee information, document uploads, and profile management

### 📋 Request Management
- **Permission Requests**: Submit and track permission requests with multi-level approval workflow
- **Leave Requests**: Comprehensive leave management system with Team Lead and Director approval
- **Travel Requests**: Submit travel requests with budget tracking and approval workflow
- **Conveyance Claims**: Submit and track conveyance/transportation expense claims
- **Asset Requests**: Request company assets with approval workflow

### 📊 Project Management
- **Project Creation & Management**: Create and manage organizational projects
- **Task Assignment**: Assign tasks to team members with priority and deadline tracking
- **Personal Projects**: Individual project and task management
- **Team Management**: Create and manage teams with member assignments
- **Group Management**: Project-specific groups for better collaboration

### 📢 Communication
- **Announcements**: Company-wide or department-specific announcements
- **Real-time Notifications**: Stay updated with request statuses and task assignments

### 📈 Reporting & Analytics
- **Attendance Tracking**: Integration with Google Drive for attendance management
- **Employee Performance**: Performance evaluation system
- **PDF Report Generation**: Generate professional reports using ReportLab
- **Dashboard Analytics**: Comprehensive dashboards for different user roles

### 🔧 Additional Features
- **Vendor Management**: Manage vendor information and relationships
- **File Upload System**: Secure file upload for documents and attachments
- **Database Migration Tools**: Built-in database migration endpoints
- **Multi-dashboard Support**: Customized dashboards based on user roles

## 🛠️ Technology Stack

### Backend
- **Flask**: Python web framework
- **SQLAlchemy**: ORM for database management
- **Flask-SQLAlchemy**: Flask integration for SQLAlchemy
- **SQLite**: Local database storage
- **Firebase Admin SDK**: Cloud database and authentication

### Frontend
- **HTML5/CSS3**: Modern responsive design
- **JavaScript**: Interactive UI components
- **Bootstrap** (implied): Responsive layout

### Libraries & Tools
- **Werkzeug**: Security utilities for password hashing
- **Pandas**: Data manipulation and analysis
- **Google APIs**: Integration with Google Drive and Sheets
- **ReportLab**: PDF generation
- **WeasyPrint**: PDF generation from HTML
- **PyTZ**: Timezone management (Asia/Kolkata)

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/bhargavikorimi/ERP-Web-Project.git
   cd ERP-Web-Project
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Create a `firebase-service-account.json` file with your Firebase credentials
   - Update the `app.secret_key` in `app.py` for production use

5. **Create necessary folders**
   ```bash
   mkdir uploads
   ```

6. **Initialize the database**
   ```bash
   python app.py
   ```
   The database will be automatically created on the first run.

7. **Run the application**
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5000`

## 🚀 Deployment

### Production Deployment with Passenger WSGI

This application is configured for deployment with Passenger WSGI (common on shared hosting).

1. **Update Configuration**
   - Ensure `firebase-service-account.json` is in the root directory
   - Update `passenger_wsgi.py` if needed

2. **Deploy**
   - Upload files to your server
   - Ensure `wsgi.py` is properly configured
   - Restart your web server

### Environment Variables

For production, set the following:
- `SECRET_KEY`: Flask secret key (change from default)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Firebase credentials
- `DATABASE_URI`: Database connection string (optional)

## 📂 Project Structure

```
ERP-Web-Project/
├── app.py                          # Main application file
├── wsgi.py                         # WSGI entry point
├── passenger_wsgi.py               # Passenger WSGI configuration
├── requirements.txt                # Python dependencies
├── users.db                        # SQLite database (auto-generated)
├── static/                         # Static files
│   ├── images/                     # Image assets
│   │   └── logo.png
│   └── videos/                     # Video backgrounds
├── templates/                      # HTML templates
│   ├── index.html                  # Landing page
│   ├── login.html                  # Login page
│   ├── register.html               # Registration page
│   ├── dashboard.html              # Main dashboard
│   ├── multi_dashboard.html        # Multi-role dashboard
│   ├── evaluation_start.html       # Evaluation start page
│   └── evaluation_evaluate.html    # Evaluation form
├── uploads/                        # User uploaded files (gitignored)
└── firebase-service-account.json   # Firebase credentials (gitignored)
```

## 🎯 Usage

### Default Login
After first setup, create an admin user through the registration page and assign appropriate roles through the database or admin panel.

### User Roles
1. **Managing Director**: Full system access, final approval authority
2. **Team Lead**: Team management, initial approval for leave and permissions
3. **HR**: Employee management, HR requests handling
4. **Accounts**: Financial requests and conveyance claims
5. **Employee**: Basic access to personal requests and tasks

## 🔒 Security Considerations

⚠️ **Important**: Before deploying to production:

1. Change the `app.secret_key` in `app.py`
2. Never commit `firebase-service-account.json` to version control
3. Use environment variables for sensitive configuration
4. Enable HTTPS in production
5. Regularly update dependencies
6. Implement rate limiting for API endpoints
7. Add CSRF protection for forms

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is proprietary and confidential. All rights reserved.

## 👥 Authors

- **Bhargavi Korimi** - [GitHub Profile](https://github.com/bhargavikorimi)

## 📧 Support

For support and queries, please open an issue in the GitHub repository.

## 🙏 Acknowledgments

- Flask framework and its extensive ecosystem
- Firebase for backend services
- Google APIs for integration capabilities
- All contributors who have helped improve this project

---

**Note**: This is an internal ERP system. Ensure all sensitive data and credentials are properly secured before deployment.

