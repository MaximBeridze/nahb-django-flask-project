# 📖 NAHB --- Not Another Hero's Book

## Project Presentation

**NAHB (Not Another Hero's Book)** is an interactive storytelling web
platform inspired by *Choose Your Own Adventure* narratives.\
The application allows authors to design branching storylines composed
of scenes and player choices, while readers can play through stories and
reach multiple possible endings based on their decisions.

The project uses a service-oriented architecture separating narrative
content management from gameplay and user interaction systems.

------------------------------------------------------------------------

## Concept

The platform supports two main user experiences:

### Authors

-   Create and manage interactive stories\
-   Build narrative trees using pages and choices\
-   Control story visibility (draft / published / suspended)

### Players

-   Browse available stories\
-   Play through branching narratives\
-   Reach multiple endings\
-   Rate and comment on stories\
-   Report inappropriate content

------------------------------------------------------------------------

## System Architecture

The project is composed of two independent applications communicating
through a REST API.

### Flask --- Narrative Content Service

Responsible for storing and managing: - Stories\
- Pages (scenes)\
- Choices (transitions)

Exposes a JSON REST API consumed by the Django application.

------------------------------------------------------------------------

### Django --- Gameplay & User Platform

Responsible for: - User interface and templates\
- Gameplay engine\
- User authentication and roles\
- Play session tracking\
- Statistics and analytics\
- Community features (ratings, comments, reports)

------------------------------------------------------------------------

## Data Separation

  Category            Managed By
  ------------------- ------------
  Narrative Content   Flask
  Gameplay Data       Django
  User Accounts       Django
  Community Data      Django

------------------------------------------------------------------------

## Core Features

### Interactive Story Engine

-   Branching story navigation\
-   Multiple endings\
-   Named endings\
-   Choice-based progression

### Gameplay Tracking

-   Play history tracking\
-   Ending distribution statistics\
-   Player path visualization\
-   Anonymous and authenticated play support

### Author Tools

-   Story creation and editing\
-   Page and choice management\
-   Draft / Published workflow\
-   Story moderation system

### Security & Permissions

-   Authentication system\
-   Role-based access control\
-   Story ownership enforcement\
-   API key protection for content modification

### Community Features

-   Story rating system (1--5 stars)\
-   Comment system\
-   Reporting system for moderation

------------------------------------------------------------------------

## Advanced Features

### Visualization

-   Story tree graph visualization\
-   Player decision path visualization

### Narrative Enhancements

-   Story illustrations support\
-   Random event / dice logic support\
-   Immersive narrative design

------------------------------------------------------------------------

## Stories

**SCP-6767 --- The King In Yellow**

Possible endings: - Containment Ending\
- Death Ending\
- King Ending

------------------------------------------------------------------------

## Technologies Used

### Backend

-   Python\
-   Django\
-   Flask\
-   SQLAlchemy

### Database

-   SQLite

### Frontend

-   Django Templates\
-   HTML / CSS / JavaScript

### Communication

-   REST API (JSON)

------------------------------------------------------------------------

## How To Setup

### Clone Repository

    git clone <repository-url>
    cd NAHB_project

### Setup Flask API

    cd flask_api
    python -m venv .venv
    .venv\Scripts\activate   (Windows)
    source .venv/bin/activate  (Mac/Linux)

    pip install -r requirements.txt
    python app.py

Flask API runs on:

    http://127.0.0.1:5001

### Setup Django Web App

    cd ../django_web
    python -m venv .venv
    .venv\Scripts\activate

    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver 8000

Django runs on:

    http://127.0.0.1:8000

------------------------------------------------------------------------

## Flask API Endpoints

### Reading

    GET /stories?status=published
    GET /stories/<id>
    GET /stories/<id>/start
    GET /pages/<id>

### Writing

    POST /stories
    PUT /stories/<id>
    DELETE /stories/<id>
    POST /stories/<id>/pages
    POST /pages/<id>/choices

Write endpoints require:

    X-API-KEY: <secret>

------------------------------------------------------------------------

## Security

Implemented protections: - CSRF protection (Django)\
- API Key validation (Flask write endpoints)\
- Role-based permissions\
- Story ownership enforcement

------------------------------------------------------------------------

## Academic Context

Developed as part of a web architecture and backend systems module
focusing on multi-service application design and REST API integration.
