# Understanding this project

Before presenting the project, work through these questions and write your own answers.

1. Run the pipeline from a new virtual environment. Which files are source inputs, and which are derived outputs?
2. Explain the difference between the survey reference period, download time and analysis generation time.
3. Find the two geography IDs in official metadata. Why must code, name and geography type all be checked?
4. Explain why adjacent survey windows overlap and why this is not a causal design.
5. Inspect `number()` and explain why suppressed values must remain missing rather than zero.
6. Read the SQL query. Explain its joins, GROUP BY, HAVING, common-period selection and percentage-point calculation.
7. Explain why inactivity is not unemployment, and identify each denominator.
8. Open the quality report and find the raw data hash. What would change when ONS revises past estimates?
9. Describe two limitations and one additional dataset you would use before advising a policymaker or business.
10. Change one chart label or extend a validated indicator in a separate local version, then rerun the tests. Be able to explain your change.

The first interview story should explain the question, data checks, SQL comparison, findings and limitations in two minutes. Do not claim the project is finished or personally reviewed before completing that review.
