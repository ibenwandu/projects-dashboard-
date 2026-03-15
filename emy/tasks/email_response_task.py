import asyncio
import logging
from typing import Dict, Optional
from emy.tools.email_tool import EmailClient
from emy.tools.email_parser import EmailParser
from emy.agents.research_agent import ResearchAgent
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.project_monitor_agent import ProjectMonitorAgent
from emy.config.celery_config import celery_app

logger = logging.getLogger(__name__)

# Map intents to agent classes
AGENT_INTENT_MAP = {
    'feedback': ResearchAgent,
    'research': KnowledgeAgent,
    'question': KnowledgeAgent,
    'status': ProjectMonitorAgent,
    'other': None  # No response for unclassified
}

async def process_and_respond_to_email(email: Dict) -> Dict:
    """
    Process email and generate agent response.

    Args:
        email: Email dict with id, sender, subject, body, intent

    Returns:
        Dict with status (response_sent/no_response/error) and details
    """
    intent = email.get('intent', 'other')
    sender = email.get('sender')
    subject = email.get('subject', '')
    body = email.get('body', '')

    # No response for unclassified emails
    if intent == 'other':
        logger.info(f"Skipping response: unclassified email from {sender}")
        return {
            'status': 'no_response',
            'reason': 'unclassified_intent',
            'email_id': email.get('id')
        }

    try:
        # Get appropriate agent for intent
        agent_class = AGENT_INTENT_MAP.get(intent)
        if not agent_class:
            logger.warning(f"No agent mapped for intent: {intent}")
            return {'status': 'no_response', 'reason': 'no_agent_mapped'}

        # Instantiate agent and generate response
        agent = agent_class()
        response = await agent.generate_email_response(
            from_email=sender,
            subject=subject,
            body=body,
            intent=intent
        )

        if not response:
            logger.info(f"Agent declined to respond to email from {sender}")
            return {'status': 'no_response', 'reason': 'agent_declined'}

        # Send response via EmailClient
        email_client = EmailClient()
        success = await email_client.send(
            to=response['to'],
            subject=response['subject'],
            body=response['body'],
            html=True
        )

        if success:
            logger.info(f"Response sent to {response['to']}")
            return {
                'status': 'response_sent',
                'recipient': response['to'],
                'email_id': email.get('id')
            }
        else:
            logger.error(f"Failed to send response to {response['to']}")
            return {
                'status': 'error',
                'reason': 'send_failed',
                'email_id': email.get('id')
            }

    except Exception as e:
        logger.error(f"Error processing email response: {e}")
        return {
            'status': 'error',
            'reason': str(e),
            'email_id': email.get('id')
        }

@celery_app.task(bind=True)
def trigger_response_generation(self, email_id: str, intent: str, sender: str, subject: str, body: str):
    """
    Celery task: Generate and send response to email.

    Called by polling task when new email processed.
    """
    email = {
        'id': email_id,
        'sender': sender,
        'subject': subject,
        'body': body,
        'intent': intent
    }

    result = asyncio.run(process_and_respond_to_email(email))
    logger.info(f"Response generation result: {result}")

    return result
