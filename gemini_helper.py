import json
from google import genai

from automation_registry import AUTOMATIONS


# ============================================================
# BUILD AUTOMATION CONTEXT
# ============================================================

def build_automation_context():

    context = []

    for automation in AUTOMATIONS:

        context.append({
            "id": automation["id"],
            "name": automation["name"],
            "category": automation["category"],
            "status": automation["status"],
            "description": automation["description"],
            "use_when": automation["use_when"],
            "input": automation["input"],
            "output": automation["output"],
            "scope": automation["scope"],
            "tags": automation["tags"]
        })

        if "feeds_into" in automation:
            context[-1]["feeds_into"] = automation["feeds_into"]

        if "dependencies" in automation:
            context[-1]["dependencies"] = automation["dependencies"]

    return json.dumps(context, indent=2)


# ============================================================
# IDENTIFY AUTOMATION
# ============================================================

def identify_automation(user_request, api_key):

    if not api_key:
        raise ValueError(
            "Please enter your Gemini API key."
        )

    # Create client using the key supplied by the user
    client = genai.Client(
        api_key=api_key
    )

    automation_context = build_automation_context()

    prompt = f"""
You are the AI orchestration assistant for an
Analytics Enablement Automation Hub.

Your job is to understand the user's request and
identify the most appropriate EXISTING automation
from the automation catalogue.

You are NOT the automation itself.

You should recommend an existing automation rather
than performing the underlying task.

IMPORTANT RULES:

1. ONLY recommend automations that exist in the
   provided catalogue.

2. NEVER invent an automation.

3. Use the automation ID EXACTLY as provided.

4. Consider the description, use cases, inputs,
   outputs, scope, tags and relationships.

5. If multiple automations are required, identify
   the primary automation and list the others in
   the sequence.

6. If no existing automation can satisfy the
   request, return NO_MATCH.

7. If an automation is marked "Work in Progress",
   clearly state that it is WIP.

8. Do not request or process sensitive information.

9. The user's actual URLs, GA4 requests, client data,
   credentials and files should NOT be sent to Gemini
   merely for automation selection.

10. Your job is ONLY to determine which automation
    should be used.

AVAILABLE AUTOMATIONS:

{automation_context}

USER REQUEST:

{user_request}

Return ONLY valid JSON.

For a successful match:

{{
    "result": "MATCH",
    "recommended_automation": "automation_id",
    "confidence": "HIGH",
    "reason": "short explanation",
    "required_input": [
        "input required from the user"
    ],
    "alternative_automations": []
}}

For no match:

{{
    "result": "NO_MATCH",
    "recommended_automation": null,
    "confidence": "LOW",
    "reason": "explanation",
    "required_input": [],
    "alternative_automations": []
}}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text