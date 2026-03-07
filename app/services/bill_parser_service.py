"""Service for parsing medical bills using AI/LLM."""

import logging
import json
from typing import List
from fastapi import HTTPException, status
from app.utils.bedrock_client import bedrock_vision_completion
from app.schemas.bills import BillParsed, BillDetail

logger = logging.getLogger(__name__)


def get_bill_parsing_prompt() -> str:
    """Generate the parsing prompt for bill extraction."""
    
    return """
        You are a medical bill parser specialized in extracting structured information from medical bills and invoices.

        Your task is to parse the provided medical bill and extract:
        1. **Bill name**: The type of bill (e.g., "Hospital Bill", "Pharmacy Bill", "Lab Charges Bill", "Consultation Bill", "Surgery Bill")
        2. **Details**: All bill items/services with their costs. For each item extract:
        - **name**: Item/service name (e.g., "Room Charges", "Medication - Aspirin", "Blood Test", "Doctor Consultation")
        - **cost**: Cost of the item (preserve the format from the bill, e.g., "5000", "1500.50", "₹2000", "$100")
        3. **Total**: The total bill amount (preserve the format from the bill, e.g., "25000", "₹50000", "$1500.75")

        IMPORTANT RULES:
        - Extract ALL bill items from the document, not just major ones
        - For each item, capture the exact name as shown in the bill
        - Preserve the cost format exactly as shown (including currency symbols, decimals, etc.)
        - The total should match the final total shown on the bill
        - If the bill has subtotals or tax breakdowns, include them as separate items if they are listed
        - Group related items if they are listed together (e.g., "Medication - Aspirin 500mg" not just "Aspirin")

        IMPORTANT: Return ONLY a valid JSON object with this exact structure:
        {{
            "name": "string (bill name/type)",
            "details": [
                {{
                    "name": "string (item/service name)",
                    "cost": "string (cost amount)"
                }}
            ],
            "total": "string (total bill amount)"
        }}

Do not include any explanations, markdown formatting, or additional text. Return ONLY the JSON object.
"""

async def parse_bill_with_vision(image_bytes_list: list[bytes]) -> BillParsed:
    """
    Parse medical bill using AWS Bedrock vision model (image-based parsing).
    Model is set via BEDROCK_MODEL in .env (see app.utils.bedrock_client).
    """
    try:
        logger.info(f"Initializing Bedrock vision model for parsing {len(image_bytes_list)} bill images")
        prompt = get_bill_parsing_prompt()
        user_text = prompt + "\n\nAnalyze the following medical bill images:"
        response_text = await bedrock_vision_completion(
            system_prompt="You are a medical bill parser.",
            user_text=user_text,
            image_bytes_list=image_bytes_list,
        )
        
        logger.info(f"Vision model response received: {len(response_text)} characters")
        logger.debug(f"Response preview: {response_text[:200]}...")
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            parsed_json = json.loads(response_text)
            logger.info("Successfully parsed AI response to JSON")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            logger.error(f"Response text: {response_text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI returned invalid JSON: {str(e)}"
            )
        
        # Convert JSON to Pydantic model
        try:
            details = []
            for detail_data in parsed_json.get("details", []):
                bill_detail = BillDetail(
                    name=detail_data.get("name") or "Unknown",
                    cost=detail_data.get("cost") or "0"
                )
                details.append(bill_detail)
            
            # Create final parsed result
            result = BillParsed(
                name=parsed_json.get("name") or "Medical Bill",
                details=details,
                total=parsed_json.get("total") or "0"
            )
            
            logger.info(f"Successfully parsed bill: {result.name} with {len(result.details)} items, total: {result.total}")
            return result
            
        except Exception as e:
            logger.error(f"Error converting parsed data to Pydantic model: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to structure parsed data: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing bill with vision: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse bill with vision: {str(e)}"
        )

