# Quick Start Guide: Using MCQ Problems

## For Problem Setters (Admins/Authors)

### Step 1: Create an MCQ Problem
1. Log in to Django Admin
2. Go to **Judge > Problems > Add Problem**
3. Fill in basic information:
   - **Code**: Unique problem identifier (e.g., `mcq_python_basics`)
   - **Name**: Display name (e.g., "Python Basics Quiz")
   - **Description**: Problem description (can include instructions)
   - **is MCQ problem**: ✅ **CHECK THIS BOX**
   - **Points**: Total points for the problem
   - **Partial**: Check if you want to award partial credit
4. Configure access:
   - **is public**: Check to make it visible to all users
   - **Authors/Curators**: Add yourself
   - **Group**: Select appropriate category
5. Click **Save**

### Step 2: Add MCQ Questions
After saving the problem, scroll down to the **MCQ Questions** section:

1. Click **"Add another MCQ question"**
2. Fill in:
   - **Order**: Question number (1, 2, 3, etc.)
   - **Question text**: The question to display
   - **Points**: Points for this question (e.g., 1.0)
   - **Allow multiple**: Check if multiple answers can be selected
   - **Explanation**: Optional explanation shown after answering
3. Repeat for all questions
4. Click **Save**

### Step 3: Add Answer Options
You have two ways to add options:

**Option A - From Problem Admin:**
1. After saving the problem, you'll see "MCQ questions" links
2. Click on a question link
3. Scroll to **"MCQ options"** section
4. Click **"Add another MCQ option"**
5. Fill in:
   - **Order**: Option number (1, 2, 3, 4, etc.)
   - **Option text**: The answer text
   - **is correct**: ✅ Check for correct answer(s)
6. Add all options (typically 4-5 per question)
7. Click **Save**

**Option B - From MCQ Questions Admin:**
1. Go to **Judge > MCQ Questions**
2. Find your question and click on it
3. Follow steps 3-7 from Option A above

### Important Notes:
- ✅ At least ONE option must be marked as correct per question
- ✅ For single-choice questions: Mark only ONE option as correct
- ✅ For multiple-choice questions: Can mark multiple options as correct
- ⚠️ Order numbers determine display order

## For Students

### Submitting MCQ Answers
1. Navigate to the problem page
2. Read the problem description
3. Click **"Submit answers"** button (NOT "Submit solution")
4. You'll see all questions with:
   - Radio buttons (⚙) for single-choice questions
   - Checkboxes (☑) for multiple-choice questions
5. Select your answers
6. Click **"Submit Answers"**
7. View results in the submission status page

### Understanding Results
- **AC (Accepted)**: All questions answered correctly
- **AC with partial points**: Some questions correct (if partial credit enabled)
- **WA (Wrong Answer)**: No questions correct or partial credit disabled

## Example MCQ Problem Structure

```
Problem: Python Basics Quiz (15 points total)
├── Question 1 (Order: 1, Points: 5, Single Choice)
│   ├── Option 1: "int" [CORRECT]
│   ├── Option 2: "string"
│   ├── Option 3: "float"
│   └── Option 4: "boolean"
│
├── Question 2 (Order: 2, Points: 5, Multiple Choice)
│   ├── Option 1: "List" [CORRECT]
│   ├── Option 2: "String"
│   ├── Option 3: "Dictionary" [CORRECT]
│   └── Option 4: "Integer"
│
└── Question 3 (Order: 3, Points: 5, Single Choice)
    ├── Option 1: "True" [CORRECT]
    ├── Option 2: "False"
    └── Option 3: "None"
```

## Tips for Problem Setters

1. **Question Order**: Use increments of 1 (1, 2, 3...) for easy management
2. **Option Order**: Use similar increments (1, 2, 3, 4)
3. **Point Distribution**: Make sure question points add up logically
4. **Partial Credit**: Enable if you want to reward partial knowledge
5. **Clear Questions**: Write unambiguous questions
6. **Balanced Options**: Include plausible distractors
7. **Testing**: Submit test answers before making public

## Troubleshooting

**Problem: "This is not an MCQ problem" error**
- Solution: Make sure "is MCQ problem" checkbox is checked in problem settings

**Problem: No questions appear in submission page**
- Solution: Add MCQ questions and options in admin panel

**Problem: Can't mark problem as MCQ**
- Solution: You need appropriate permissions (author/curator/admin)

**Problem: Students see "Submit solution" instead of "Submit answers"**
- Solution: Clear browser cache or check that "is MCQ problem" is checked

## Admin URLs
- Problems: `/admin/judge/problem/`
- MCQ Questions: `/admin/judge/mcqquestion/`
- Submissions: `/admin/judge/submission/`
