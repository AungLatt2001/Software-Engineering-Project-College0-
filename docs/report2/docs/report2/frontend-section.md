# Frontend Contribution – College0

## 1. Frontend Overview

My role in the College0 project is the frontend development of the system.  
I am responsible for the client-side interface, including page layout, navigation, forms, and user interaction flow.

The frontend was designed to allow visitors, students, instructors, and administrators to interact with the College0 academic portal through a clear and organized graphical interface.

To test the interface locally, a temporary/mock backend was used so that navigation, authentication flow, and page behavior could be verified.  
However, my main contribution is the frontend implementation of the system.

## 2. System Screens

The following major frontend screens were developed for College0.

### 2.1 Login Screen

The login screen allows users to enter their user ID and password in order to access the portal.  
It includes a sign-in form, demo credential guidance, and error handling for invalid login attempts.

**Figure 1. Login screen of College0.**  
This interface allows users to authenticate and access the academic portal.

### 2.2 Home / Public Page

The home page presents an overview of the academic portal.  
It includes campus summary information, highlighted academic statistics, top-rated courses, top GPA students, and the course catalogue.

**Figure 2. Public home page of College0.**  
This screen presents an overview of the portal, including academic statistics, featured courses, and the course catalogue.

### 2.3 Apply Screen

The application screen allows visitors to submit an application to join the system as a student or instructor.  
It includes form fields for identity, email, role selection, GPA, and an optional statement.

**Figure 3. Application screen.**  
This page allows visitors to submit an application to the system.

### 2.4 AI Assistant Screen

The AI Assistant page provides a user interface where users can ask academic or portal-related questions.  
The frontend supports text input, quick question buttons, and response display.

**Figure 4. AI Assistant interface.**  
This page allows users to submit questions and interact with the assistant interface.

### 2.5 Student Dashboard

The student dashboard is shown after successful login and displays personalized academic information such as GPA, warning count, enrolled courses, and completed courses.

**Figure 5. Student dashboard.**  
This dashboard provides a personalized academic overview for the logged-in student.

### 2.6 My Courses Screen

The My Courses page displays the courses currently enrolled by the student and related semester information.

**Figure 6. My Courses screen.**  
This page displays the student’s enrolled courses and semester registration details.

### 2.7 Transcript Screen

The transcript page presents the academic record of the student, including cumulative GPA, warning count, honor count, and completed courses with grades.

**Figure 7. Academic Transcript screen.**  
This page shows the student’s academic record and performance summary.

### 2.8 Reviews & More Screen

The Reviews & More page provides access to review submission, graduation-related features, and complaint-related actions.  
It supports tabbed interaction and form input.

**Figure 8. Reviews & More screen.**  
This page provides access to review, graduation, and complaint functions.

## 3. Sample Prototype

### Prototype Chosen: Login Functionality

The login functionality was selected as the sample prototype because it is one of the most important entry points in the system and demonstrates the interaction between the frontend and backend clearly.

**Input:**
- User ID
- Password

**Process:**
1. The user enters the login credentials.
2. The frontend validates that the required fields are filled.
3. The frontend sends the credentials to the backend for authentication.
4. If authentication is successful, the user is redirected to the correct dashboard.
5. If authentication fails, an error message is displayed and the user can try again.

**Output:**
- Successful login and dashboard access
- Authentication error message

## 4. Frontend Use Cases

### 4.1 Use Case: User Login

**Normal scenario**
1. User opens the login screen.
2. User enters a valid user ID and password.
3. User clicks the Sign In button.
4. Frontend sends the login request to the backend.
5. Backend validates the credentials.
6. Frontend receives a successful response.
7. User is redirected to the correct dashboard.

**Exceptional scenario**
1. User enters an incorrect ID or password.
2. Frontend sends the login request.
3. Backend rejects the credentials.
4. Frontend displays an error message.
5. User stays on the login screen and tries again.

### 4.2 Use Case: Submit Application

**Normal scenario**
1. Visitor opens the Apply page.
2. Visitor fills in the application form.
3. Visitor selects the desired role.
4. Visitor enters GPA and optional statement.
5. Visitor clicks Submit Application.
6. Frontend validates the form.
7. Application data is sent to the backend.
8. Confirmation is displayed.

**Exceptional scenario**
1. Visitor leaves required fields empty or enters invalid data.
2. Frontend validation fails or backend rejects the request.
3. An error message is displayed.
4. Visitor corrects the form and resubmits.

### 4.3 Use Case: Ask AI Assistant

**Normal scenario**
1. User opens the AI Assistant page.
2. User enters a question in the text area.
3. User clicks Ask AI.
4. Frontend sends the question to the backend.
5. Backend processes the request and returns a response.
6. Frontend displays the answer.

**Exceptional scenario**
1. User submits an empty question or the backend is unavailable.
2. Frontend detects the issue or receives an error.
3. An error message or loading failure is shown.

## 5. Sequence Flow

### 5.1 Login Sequence

**User → Login Screen → Backend → Frontend → Dashboard**

1. User enters login credentials.
2. Frontend sends authentication request to backend.
3. Backend checks the submitted credentials.
4. Backend returns success or failure.
5. Frontend shows an error or redirects to the dashboard.

### 5.2 Application Sequence

**Visitor → Apply Screen → Backend → Frontend**

1. Visitor fills out the application form.
2. Frontend validates user input.
3. Frontend sends application data to backend.
4. Backend stores the application.
5. Frontend displays confirmation or error.

### 5.3 AI Assistant Sequence

**User → AI Assistant Screen → Backend → Frontend**

1. User enters a question.
2. Frontend sends the question to the backend.
3. Backend processes the request.
4. Backend returns a response.
5. Frontend displays the returned answer.

## 6. Detailed Design – Frontend Pseudocode

### 6.1 handleLogin()

**Input:** user ID, password  
**Output:** dashboard page or error message

1. Read user ID and password from the login form.
2. Validate that both fields are filled.
3. If a field is missing, display a validation error.
4. Send login request to backend API.
5. Wait for authentication response.
6. If authentication is successful:
   - save user session information
   - redirect to the correct dashboard
7. Else:
   - display login failure message

### 6.2 handleApply()

**Input:** application form data  
**Output:** success message or error message

1. Read application fields from the form.
2. Validate required fields.
3. If input is invalid, display an error.
4. Send application data to backend API.
5. Wait for response.
6. If submission succeeds:
   - display confirmation message
7. Else:
   - display error message

### 6.3 handleAskAI()

**Input:** user question  
**Output:** response or error message

1. Read question from AI input field.
2. Check that the question is not empty.
3. Send the question to backend API.
4. Show loading indicator.
5. Wait for response.
6. If response is successful:
   - display answer in the interface
7. Else:
   - display error message

### 6.4 loadDashboard()

**Input:** authenticated user role  
**Output:** role-based dashboard content

1. Identify current user role.
2. Request role-specific data from backend.
3. Wait for response.
4. If data is received:
   - render dashboard components
5. Else:
   - show loading or error state

## 7. Frontend Responsibilities

The frontend is responsible for:
- displaying system pages and layout
- navigation between pages
- collecting user input
- validating forms at the interface level
- sending requests to the backend
- displaying returned information
- showing loading, success, and error states

The frontend is not responsible for:
- backend business logic
- permanent data storage
- database operations
- authentication processing itself
- AI computation itself

These responsibilities belong to the backend and database layers.

## 8. Testing Note

The frontend was tested locally with a temporary/mock backend in order to verify the interface, navigation, authentication flow, and interactive page behavior.

Some pages depend on backend responses, so they may not fully display their final data without complete backend and database integration.  
The prototype is therefore intended to demonstrate frontend structure and interaction flow rather than final production data.

## 9. Frontend Contribution Summary

My contribution to College0 focuses on the frontend interface of the system.  
I worked on the graphical layout, role-based page navigation, forms, and interactive user screens.

I also verified the screen flow using a temporary/mock backend to ensure that the interface behaves correctly during testing.
