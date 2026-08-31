import aiohttp
import json

class MeetingSummarizer:
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    async def generate_incremental_summary(self, new_transcript: str, current_summary: str) -> str:
        """
        Takes the existing summary and updates it with the latest transcript snippet using local Ollama.
        """
        prompt = f"""
        You are an AI meeting assistant. Update the current meeting summary with the new transcript.
        Current Summary:
        {current_summary}
        
        New Transcript:
        {new_transcript}
        
        Provide an updated, concise summary.
        """
        return await self._call_ollama(prompt) or current_summary

    async def generate_final_summary(self, full_transcript: str) -> str:
        """
        Generates a comprehensive per-speaker executive summary using local Ollama.
        """
        prompt = f"""
# SPEAKER-WISE MEETING ANALYSIS PROMPT

## ROLE

You are an expert Meeting Intelligence AI.

Your task is to analyze a meeting transcript and generate a **speaker-wise summary**.

The transcript may contain multiple speakers such as:

* Speaker A
* Speaker B
* Speaker C
* Speaker D
* Speaker E
* etc.

Your most important responsibility is to **group all statements belonging to the same Speaker ID together**, even when that speaker appears many times throughout the transcript.

Do NOT summarize each timestamp separately.

Instead, create **one complete consolidated analysis for each unique Speaker ID**.

---

# CORE INSTRUCTION

First identify every unique Speaker ID in the transcript.

For each Speaker ID:

1. Collect ALL statements spoken by that speaker.
2. Combine those statements together logically.
3. Identify all major topics discussed by that speaker.
4. Identify technical, professional, domain-specific, or important terminology used by that speaker.
5. Determine the overall conclusion/message of that speaker's entire contribution.
6. Identify important decisions, actions, recommendations, requirements, dates, numbers, or commitments mentioned by that speaker.
7. Do not mix information from other speakers into that speaker's summary.

If Speaker A speaks 15 different times during the meeting, treat all 15 sections as belonging to **one Speaker A** and produce only **one Speaker A summary**.

---

# IMPORTANT SOURCE RULE

Use ONLY information supported by the provided transcript.

Do not invent information.

Do not assume a speaker's job title, department, role, intention, or background unless the transcript explicitly supports it.

If something is unclear because of transcription errors, say:

"Not clearly stated in the transcript."

Do not silently correct or invent missing information.

If a technical term appears to be incorrectly transcribed, preserve the transcript wording and, when the intended meaning is clear from surrounding context, mention the likely interpretation separately.

---

# REQUIRED OUTPUT STRUCTURE

For every unique speaker, use exactly this structure:

## 1. Total Summary — Speaker [ID]

### 1) What did Speaker [ID] speak about?

Provide a consolidated summary of everything this speaker discussed throughout the meeting.

Organize the discussion into major themes.

For example:

* Topic 1

  * Explanation
  * Important details

* Topic 2

  * Explanation
  * Important details

* Topic 3

  * Explanation
  * Important details

Do NOT organize this section by timestamp.

Do NOT repeat the same information multiple times.

Combine related statements from different parts of the transcript.

---

### 2) Technical / Professional / Specialized Words Used

Extract important terminology used by this speaker.

Include:

* Technical terms
* Industry terminology
* Professional terminology
* Business terminology
* Academic terminology
* Legal terminology
* Medical terminology
* Financial terminology
* Software/IT terminology
* Product/project terminology
* Important acronyms

For each important term, provide a short meaning based on the meeting context.

Format:

| Term   | Meaning in this meeting |
| ------ | ----------------------- |
| Term 1 | Explanation             |
| Term 2 | Explanation             |
| Term 3 | Explanation             |

Do NOT call ordinary conversational words "technical terms."

Only include meaningful specialized terminology.

---

### 3) Final Summary of Speaker [ID]

Provide a concise but complete conclusion of the speaker's entire contribution.

Answer:

* What was the main message?
* What was the speaker trying to communicate?
* What should the listener understand after hearing this speaker?
* What was the overall conclusion?

Write this as a clear paragraph.

---

### 4) Key Information / Actions

Extract important actionable information from this speaker.

Include things such as:

* Decisions
* Requirements
* Instructions
* Recommendations
* Action items
* Deadlines
* Dates
* Numbers
* Responsibilities
* Follow-up actions
* Important warnings
* Important commitments

If there are no clear actions, write:

"No specific action items were identified from this speaker."

---

### 5) Speaker Contribution in One Sentence

Give one sentence describing this speaker's overall contribution.

Format:

**Speaker [ID] mainly contributed by [short description].**

---

# NEXT SPEAKER

After completing Speaker A, continue with:

## 2. Total Summary — Speaker B

Use the same structure.

Then:

## 3. Total Summary — Speaker C

Then:

## 4. Total Summary — Speaker D

Continue until **every unique Speaker ID in the transcript has been analyzed**.

Do NOT stop at Speaker C.

Do NOT assume that only Speakers A, B, and C exist.

If the transcript contains:

Speaker A
Speaker B
Speaker C
Speaker D
Speaker E
Speaker F

then generate six speaker sections.

---

# SPEAKER SEPARATION RULE

This is extremely important.

If the transcript looks like:

Speaker A:
statement...

Speaker B:
statement...

Speaker A:
another statement...

Speaker C:
statement...

Speaker A:
another statement...

The output must be:

Speaker A = combine ALL three Speaker A sections.

Speaker B = only Speaker B.

Speaker C = only Speaker C.

Never mix speaker information.

---

# TOPIC GROUPING RULE

When one speaker discusses the same topic at different times, combine those statements.

Example:

Speaker A discusses:

10:02 — Project deadline
10:15 — Project deadline
10:40 — Project deadline

Do NOT produce three separate topics.

Instead:

**Project Deadline**

* Consolidate all relevant information from 10:02, 10:15 and 10:40.

---

# TECHNICAL TERM RULE

Technical terminology must come from the actual transcript.

For example, if the transcript contains:

"RAG", "API", "PostgreSQL", "GPU", "embedding", "vector database"

then extract those terms.

If the transcript does NOT contain technical terminology, do not invent technical terms.

If the meeting is about education, terms such as:

"admissions", "transcript", "ISEE", "SSAT", "Harkness", "reclassing"

may be considered specialized terminology.

The definition must be based on how the term is used in the transcript.

---

# FINAL SUMMARY RULE

The final summary must represent the speaker's COMPLETE contribution.

Do not summarize only the speaker's last sentence.

For example:

If Speaker A discusses:

* Project architecture
* Database
* API
* Security
* Deployment

and later talks about:

* Testing
* Timeline

the final summary must include all of these areas.

---

# DO NOT DO THESE THINGS

Do NOT:

1. Summarize only the first time a speaker appears.
2. Summarize only the last time a speaker appears.
3. Create a separate section for every timestamp.
4. Mix Speaker A information into Speaker B.
5. Invent technical terminology.
6. Invent decisions or action items.
7. Assume speaker roles without evidence.
8. Ignore repeated speaker appearances.
9. Remove important numbers, dates, deadlines, or requirements.
10. Give a generic meeting summary instead of a speaker-wise summary.
11. Assume that Speaker A is always the manager.
12. Assume that Speaker B is always an employee.
13. Assume that Speaker C is always a customer.
14. Change the meaning of what the speaker said.

---

# QUALITY REQUIREMENTS

The final output should be:

* Accurate
* Speaker-specific
* Consolidated
* Non-repetitive
* Easy to read
* Professional
* Fact-based
* Based on the transcript
* Clear about uncertainty
* Detailed enough to preserve important information

The most important priority is:

**Speaker separation -> Complete speaker aggregation -> Topic extraction -> Technical terminology -> Final conclusion -> Actions**

---

# FINAL OUTPUT EXAMPLE

## 1. Total Summary — Speaker A

### 1) What did Speaker A speak about?

Speaker A discussed the project architecture, backend services, database design, API integration, authentication, deployment strategy, and project timeline.

**Major topics:**

* **Architecture**

  * Explained the overall system architecture.
  * Described frontend, backend, and AI services.

* **Database**

  * Discussed PostgreSQL and data storage.

* **API Integration**

  * Explained how the backend communicates with external services.

* **Security**

  * Discussed authentication and authorization.

* **Deployment**

  * Explained the planned production deployment.

### 2) Technical / Professional / Specialized Words Used

| Term           | Meaning in this meeting                                          |
| -------------- | ---------------------------------------------------------------- |
| API            | Application Programming Interface used for system communication  |
| PostgreSQL     | Database system used by the project                              |
| Authentication | Process of verifying a user's identity                           |
| Authorization  | Process of controlling what an authenticated user can access     |
| Deployment     | Process of putting the application into a production environment |

### 3) Final Summary of Speaker A

Speaker A's overall contribution focused on explaining how the system will be structured, how its components communicate, how data will be stored and protected, and how the system will eventually be deployed.

### 4) Key Information / Actions

* Finalize architecture.
* Configure database.
* Complete API integration.
* Implement authentication and authorization.
* Prepare production deployment.

### 5) Speaker Contribution in One Sentence

**Speaker A mainly contributed by explaining the technical architecture, integration strategy, security approach, and deployment plan.**

---

Transcript:
{full_transcript}
"""
        return await self._call_ollama(prompt) or "Failed to generate final summary."

    async def _call_ollama(self, prompt: str) -> str:
        print(f"Calling local Ollama ({self.model_name}) for summary...")
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "system": "You are a strict, expert AI meeting analyst. You must ONLY output the requested Markdown format. Do NOT include any conversational text.",
                    "options": {
                        "temperature": 0.2
                    },
                    "stream": False
                }
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                    else:
                        error_text = await response.text()
                        print(f"Ollama error {response.status}: {error_text}")
                        return ""
        except Exception as e:
            print(f"Ollama connection error: {e}. Is the Ollama daemon running?")
            return ""
