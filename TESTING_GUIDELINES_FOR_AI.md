# SentryHub Testing Guidelines for AI Assistant

This document outlines the process and guidelines for incrementally adding tests to the SentryHub Django project using an AI assistant.

**Core Principles:**

1.  **Incremental Approach & Single Scenario Focus:** Add tests piece by piece. The AI will generate code for *only one specific test scenario* in each interaction, then stop and await results/feedback before proceeding to the next scenario. Focus on one component (model, form, view, service, etc.) at a time.
2.  **Verification:** After generating tests for a component, run them locally to ensure they pass.
3.  **Tracking:** Update the `TEST_COVERAGE_TRACKING.md` file after tests for a component are successfully written and pass.
4.  **Isolation:** Aim for unit tests where possible, mocking dependencies. Use integration tests when testing interactions between components.
5.  **Clarity:** Test names should clearly describe what they are testing. Assertions should be specific.
6.  **No `codeBase.json` Modification:** **Crucially, do not read from or modify the `codeBase.json` file.** Analyze the actual Python/JS/HTML code directly.
7.  **Check for Existing Tests:** Before writing a test, always check if a similar test already exists. If a similar test is found, ensure that it covers all necessary cases and scenarios. A test class might exist, but it might not cover all required aspects.
8.  **Limit Debugging Attempts:** To prevent getting stuck in infinite loops and incurring excessive costs, set a limit of **6 attempts** to debug and fix a failing test for a *specific test scenario*. If the test for a specific scenario still fails after this limit is reached, the *entire component* (not just the scenario) should be marked with 🟡 `Needs Review` in the `TEST_COVERAGE_TRACKING.md` file, and a note should be added to the component's entry indicating which scenario failed and that it hit the 6-attempt limit. The AI should then *stop working on that problematic scenario* and await instructions from the human operator to either move to a different scenario for the same component, move to a different component altogether, or escalate the issue for human review.
9.  **File Size and Organization:** Keep test files small and manageable. If a test file (like `tests.py` or `test_*.py`) becomes too large, split it into smaller files. A common approach is to put each test class or related group of tests into a separate file (e.g., `test_models.py`, `test_views.py`, `test_forms.py`). This improves the readability, organization, and maintainability of the test suite.

**Testing Stack:**

*   **Backend (Python/Django):**
    *   Framework: `unittest` (Python built-in) and `django.test.TestCase`.
    *   Tools: `django.test.Client`, `django.test.RequestFactory`, `django.utils.timezone`, `datetime.timedelta`.
    *   Mocking: `unittest.mock` (standard library).
    *   Fixtures/Factories: Initially manual object creation. Consider `factory-boy` later if needed.
*   **Frontend (JavaScript):**
    *   Framework: Jest (or Vitest, specify if preferred).
    *   Utilities: Testing Library (for DOM interaction testing).
    *   Mocking: Jest's built-in mocking capabilities (e.g., `jest.fn()`, `jest.mock()`).

**Workflow for Each Component:**

1.  **Identify Target:** Choose the next component to test from the `TEST_COVERAGE_TRACKING.md` file (usually one marked with ⚪️).
2.  **Generate Prompt:** Use the specific prompt template provided below, filling in the details for the target component.
3.  **Provide Context:** Ensure the AI has access to the relevant project code files.
4.  **Generate, Integrate, and Test ONE Scenario:** Ask the AI to generate code for a *single specific test scenario*. Integrate the generated code into the appropriate `tests.py` (or `test_*.py` / `*.test.js`) file, handling imports and potential conflicts. Run the newly added test(s) locally (e.g., `python manage.py test app_name.tests.TestClassName::test_specific_scenario`). Debug and refine with the AI until the test(s) pass (up to the defined 6-attempt limit). After this single scenario's test is generated, integrated, and run (and potentially debugged), the AI's current task for that interaction is complete. The decision to move to the next scenario (for the same component or a different one) will be a new instruction.
5.  **Update Tracking (Scenario Success):** If the test for the single scenario passes, the AI's task for that interaction is complete. The human operator will then decide whether to proceed with another scenario for the same component or a different component. The `TEST_COVERAGE_TRACKING.md` file will be updated by the human operator as scenarios are successfully covered for a component.
6.  **Update Tracking (Scenario Failure):** If a test for a specific scenario still fails after 6 attempts by the AI, the *entire component* (not just the scenario) should be marked with 🟡 `Needs Review` in the `TEST_COVERAGE_TRACKING.md` file. A note should be added to the component's entry indicating which scenario failed and that it hit the 6-attempt limit. The AI should then *stop working on that problematic scenario* and await instructions from the human operator.
7.  **Commit Changes:** Commit the new/updated test file and the updated tracking file.

---

## Prompt Template for AI

```text
**Previous Context:**
We are incrementally adding tests to the SentryHub Django project using the guidelines in `TESTING_GUIDELINES_FOR_AI.md`. We previously tested [Mention last successfully tested component, e.g., "the SilenceRule model"].

**Current Goal:**
Write tests for the **[Specify Component Type, e.g., Form, View, Service]** named **`[Component Name, e.g., SilenceRuleForm]`** located in **`[File Path, e.g., alerts/forms.py]`**.

**Context Files:**
Analyze the code in the following file(s) to understand the component's functionality:
*   `[File Path for the component, e.g., alerts/forms.py]`
*   [If relevant, add paths to related models, e.g., `alerts/models.py`]
*   [If relevant, add paths to related views or services]

**Testing Framework:** [Specify: `unittest` and `django.test.TestCase` OR `Jest` and `Testing Library`]

**Task:**
1.  Identify the key functionalities and potential edge cases of the `[Component Name]` based on its code.
2.  Write [Specify: `unit` or `integration`] tests for *ONLY the following specific scenario*:
    *   [Scenario 1: e.g., Test form validation with valid data.]
    *   [Scenario 2: e.g., Test form validation with invalid data (specify invalid cases, like end_date before start_date).]
    *   [Scenario 3: e.g., Test the `clean_matchers` method specifically.]
    *   [Scenario 4: e.g., Test if `form.save()` correctly creates/updates the database object.]
    *   [Scenario 5: e.g., For Views: Test GET request returns 200 and uses correct template.]
    *   [Scenario 6: e.g., For Views: Test POST request with valid data redirects/returns correct response.]
    *   [Scenario 7: e.g., For Views: Test access control/permissions.]
    *   [Scenario 8: e.g., For JS: Test function `xyz` returns expected output for inputs A and B.]
    *   [Scenario 9: e.g., For JS: Test clicking button `abc` triggers expected DOM change or API call (mock fetch).]
    *   *(Add/remove scenarios as needed based on the component)*
    *   **Note:** The AI will be prompted for other scenarios separately.
3.  [If Backend] Use `django.test.Client` or `RequestFactory` for view/API tests. Create necessary test data (e.g., Users, related model instances) within tests or `setUp` methods.
4.  [If Backend] Use `unittest.mock.patch` if dependencies need to be mocked for unit testing.
5.  [If Frontend] Use Testing Library utilities (`render`, `screen`, `fireEvent`) for interaction tests. Mock `fetch` or other external dependencies using `jest.mock`.
6.  Place the generated test code into the appropriate file: **`[Target Test File Path, e.g., alerts/tests.py or static/alerts/js/__tests__/comments.test.js]`**. Append to the file if it already contains tests, ensuring imports are handled correctly.

**Output:**
Provide the *complete code* for the newly generated test method AND any necessary new imports. If modifying an existing test class, show the context of the class with the new method added. If it's a new test file or class, provide the full file content.

**Reminder:**
*   Follow the testing stack defined in the guidelines.
*   Ensure tests are independent.
*   use this python `/Users/ali/codes/sentryHub/venv/bin/python3` to run tests
---

## Handling Components Marked for Human Review (🟡 Needs Review)

If a component in `TEST_COVERAGE_TRACKING.md` is marked with 🟡 `Needs Review` due to a test scenario failing after 6 AI attempts, it indicates a persistent issue requiring human intervention.

**Human Operator Actions:**

*   **Review `TEST_COVERAGE_TRACKING.md`:** Check the notes associated with the 🟡 `Needs Review` component entry to identify the specific scenario that failed and the attempt limit reached.
*   **Investigate:** Manually examine the component's code and the problematic test scenario.
*   **Resolve:** Fix the underlying issue in the code or the test, or determine if the scenario is untestable by the AI.
*   **Update Tracking:** Once resolved, update the component's status in `TEST_COVERAGE_TRACKING.md` accordingly (e.g., to 🟢 Done if fixed, or add a specific note if deemed untestable by AI).
*   **Re-engage AI:** If the issue is resolved, the AI can be re-engaged to continue testing other scenarios for that component or move to a new component.

---