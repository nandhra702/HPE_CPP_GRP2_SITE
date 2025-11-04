# MCQ (Multiple Choice Question) Support Implementation

## Overview
MCQ support has been successfully added to the DMOJ platform. This allows creating problems that use multiple choice questions instead of traditional code-based submissions.

## Implementation Details

### 1. Database Models (`judge/models/problem_mcq.py`)
Three new models were created:

- **MCQQuestion**: Stores individual MCQ questions for a problem
  - Fields: problem, order, question_text, explanation, points, allow_multiple
  - Supports single-choice and multiple-choice questions
  - Each question can have its own point value

- **MCQOption**: Stores answer options for each question
  - Fields: question, order, option_text, is_correct
  - Multiple options can be marked as correct for multiple-choice questions

- **MCQSubmission**: Stores user answers for MCQ submissions
  - Fields: submission (OneToOne), answers (JSON)
  - Stores answers as JSON mapping question IDs to selected option IDs
  - Includes `calculate_score()` method for automatic grading

### 2. Problem Model Update (`judge/models/problem.py`)
- Added `is_mcq` BooleanField to distinguish MCQ problems from code problems
- Defaults to False for backward compatibility

### 3. Admin Interface (`judge/admin/problem.py`)
- **MCQQuestionInline**: Inline admin for adding questions to problems
- **MCQOptionInline**: Inline admin for adding options to questions
- **MCQQuestionAdmin**: Standalone admin for managing MCQ questions and their options
- Added `is_mcq` field to Problem admin form

### 4. Forms (`judge/forms.py`)
- **MCQSubmitForm**: Dynamic form that generates radio/checkbox fields based on problem's MCQ questions
  - Single-choice questions use radio buttons
  - Multiple-choice questions use checkboxes
  - Includes `get_answers_dict()` method to convert form data to JSON format

### 5. Views (`judge/views/problem.py`)
- **MCQSubmit**: View for handling MCQ submissions
  - Validates submission limits
  - Creates Submission and MCQSubmission records
  - Automatically grades submissions using `MCQSubmission.calculate_score()`
  - Updates points based on problem's partial credit settings
  - Supports contest submissions

### 6. Templates
- **`templates/problem/mcq_submit.html`**: MCQ submission interface
  - Clean, user-friendly layout for answering questions
  - Shows point values and help text
  - Styled radio buttons and checkboxes
  - Navigation back to problem page

- **Updated `templates/problem/problem.html`**:
  - Shows "Submit answers" button for MCQ problems
  - Shows "Submit solution" button for code problems

### 7. URL Routing (`dmoj/urls.py`)
- Added `/problem/<code>/submit/mcq` route for MCQ submissions
- Maps to `MCQSubmit` view

### 8. Database Migration
- Migration `0157_problem_is_mcq_alter_profile_timezone_mcqsubmission_and_more.py` created
- Successfully applied to database

## How to Use

### Creating an MCQ Problem

1. **Create a Problem in Admin**:
   - Go to Admin > Problems > Add Problem
   - Fill in basic details (code, name, description, etc.)
   - **Check the "is MCQ problem" checkbox**
   - Set points and partial credit settings
   - Save the problem

2. **Add MCQ Questions**:
   - In the problem's admin page, scroll to "MCQ Questions" section
   - Click "Add another MCQ question"
   - Enter question text, points, and whether multiple answers are allowed
   - Save

3. **Add Options to Questions**:
   - Click on the MCQ question link or go to Admin > MCQ Questions
   - In the "MCQ Options" section, add answer options
   - Mark the correct answer(s) with the "is correct" checkbox
   - Ensure order is set properly
   - Save

### Student Submission Flow

1. Student views the problem page
2. Clicks "Submit answers" button (instead of "Submit solution")
3. Sees all questions with radio buttons (single-choice) or checkboxes (multiple-choice)
4. Selects answers and clicks "Submit Answers"
5. System automatically grades the submission:
   - AC (Accepted) if all questions correct
   - AC with partial points if some correct (if partial credit enabled)
   - WA (Wrong Answer) if no questions correct
6. Results appear in submission status page

## Grading Logic

- Each question is worth its specified points
- A question is marked correct only if ALL correct options are selected and NO incorrect options are selected
- Total score = sum of points for correct questions
- If `problem.partial` is True: student gets partial credit
- If `problem.partial` is False: student must get 100% for any points

## Future Enhancements (Optional)

1. Add per-option feedback/explanations
2. Support for randomized question/option order
3. Image support in questions and options
4. Question banks and random question selection
5. Time limits per question
6. Review mode showing correct/incorrect answers after submission
7. Export/import MCQ questions in standard formats
8. Statistics on question difficulty based on submissions

## Technical Notes

- MCQ submissions don't require a judge server (grading is instant)
- MCQ submissions use a dummy language entry (first language in database)
- Submission time and memory are set to 0
- MCQSubmission uses JSONField for flexibility in storing answers
- Compatible with contest mode and submission limits
