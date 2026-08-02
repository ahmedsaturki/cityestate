"""
Document Processing Skill — معالجة المستندات
=============================================
PDF/DOCX extraction, document analysis, and content summarization.
Supports real estate documents: contracts, deeds, inspection reports.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("skills.document_processing")


class DocumentProcessingSkill:
    """Document processing and analysis skill."""

    async def extract_text(self, file_path: str) -> dict:
        """Extract text from PDF or DOCX."""
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "error": f"File not found: {file_path}"}

        ext = path.suffix.lower()

        if ext == ".pdf":
            return await self._extract_pdf(file_path)
        elif ext in (".docx", ".doc"):
            return await self._extract_docx(file_path)
        elif ext == ".txt":
            return await self._extract_txt(file_path)
        else:
            return {"status": "error", "error": f"Unsupported file type: {ext}"}

    async def _extract_pdf(self, file_path: str) -> dict:
        """Extract text from PDF."""
        try:
            import pdfplumber

            text_parts = []
            tables = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            tables.append({
                                "page": i + 1,
                                "rows": len(table),
                                "data": table[:10],
                            })

            return {
                "status": "success",
                "file": file_path,
                "type": "pdf",
                "pages": len(text_parts),
                "text": "\n\n".join(text_parts)[:20000],
                "tables": tables[:5],
                "char_count": sum(len(t) for t in text_parts),
            }
        except ImportError:
            return {"status": "error", "error": "pdfplumber not installed. Run: pip install pdfplumber"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _extract_docx(self, file_path: str) -> dict:
        """Extract text from DOCX."""
        try:
            import docx

            doc = docx.Document(file_path)
            text_parts = []

            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            tables = []
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                tables.append({"rows": len(table_data), "data": table_data[:10]})

            return {
                "status": "success",
                "file": file_path,
                "type": "docx",
                "paragraphs": len(text_parts),
                "text": "\n".join(text_parts)[:20000],
                "tables": tables[:5],
                "char_count": sum(len(t) for t in text_parts),
            }
        except ImportError:
            return {"status": "error", "error": "python-docx not installed. Run: pip install python-docx"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _extract_txt(self, file_path: str) -> dict:
        """Extract text from plain text file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            return {
                "status": "success",
                "file": file_path,
                "type": "text",
                "text": text[:20000],
                "char_count": len(text),
                "line_count": text.count("\n") + 1,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def analyze_contract(self, file_path: str) -> dict:
        """Analyze a real estate contract document."""
        extraction = await self.extract_text(file_path)
        if extraction["status"] != "success":
            return extraction

        text = extraction["text"].lower()

        # Extract key contract elements
        elements = {
            "parties": self._extract_pattern(text, r"(?:between|بين)\s+(.+?)(?:\s+and|\s+و)"),
            "property_address": self._extract_pattern(text, r"(?:property|العقار).+?(?:located|الموقع).+?[:]\s*(.+?)(?:\.|$)"),
            "price": self._extract_pattern(text, r"(?:price|الثمن|المبلغ).+?[:]\s*(.+?)(?:\.|$)"),
            "payment_terms": self._extract_pattern(text, r"(?:payment|الدفع).+?(?:terms|الشروط).+?[:]\s*(.+?)(?:\.|$)"),
            "duration": self._extract_pattern(text, r"(?:duration|المدة).+?[:]\s*(.+?)(?:\.|$)"),
            "delivery_date": self._extract_pattern(text, r"(?:delivery|التسليم).+?(?:date|التاريخ).+?[:]\s*(.+?)(?:\.|$)"),
            "penalties": self._extract_pattern(text, r"(?:penalty|غرامة|تعويض).+?[:]\s*(.+?)(?:\.|$)"),
        }

        return {
            "status": "success",
            "file": file_path,
            "document_type": "contract",
            "text_preview": extraction["text"][:500],
            "elements": elements,
            "char_count": extraction["char_count"],
        }

    async def extract_property_details(self, file_path: str) -> dict:
        """Extract property details from a document."""
        extraction = await self.extract_text(file_path)
        if extraction["status"] != "success":
            return extraction

        text = extraction["text"]

        details = {
            "area_sqm": self._extract_number(text, r"(\d+[\.,]?\d*)\s*(?:sqm|م²|م2|m²|m2)"),
            "bedrooms": self._extract_number(text, r"(\d+)\s*(?:bedroom|غرف|room)"),
            "bathrooms": self._extract_number(text, r"(\d+)\s*(?:bath|حمام)"),
            "floor": self._extract_number(text, r"(?:floor|طابق)\s*(\d+)"),
            "price": self._extract_pattern(text, r"(\d[\d,\.]*)\s*(?:EGP|جنيه|LE|ج\.م)"),
            "year_built": self._extract_number(text, r"(?:built|بنا)\s*(\d{4})"),
            "furnished": "yes" in text.lower() and ("furnished" in text.lower() or "مفروش" in text),
        }

        return {
            "status": "success",
            "file": file_path,
            "property_details": details,
            "text_preview": text[:500],
        }

    async def batch_extract(self, file_paths: list[str]) -> list[dict]:
        """Extract text from multiple documents."""
        results = []
        for path in file_paths:
            result = await self.extract_text(path)
            results.append(result)
        return results

    def _extract_pattern(self, text: str, pattern: str) -> str | None:
        """Extract a pattern from text."""
        import re
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_number(self, text: str, pattern: str) -> float | None:
        """Extract a number from text."""
        import re
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num_str = match.group(1).replace(",", ".")
            try:
                return float(num_str)
            except ValueError:
                return None
        return None


def get_document_tools():
    """Return CrewAI-compatible tools for document processing."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class ExtractTextInput(BaseModel):
        file_path: str = Field(description="Path to document file")

    class ExtractTextTool(BaseTool):
        name: str = "extract_document_text"
        description: str = "Extract text content from PDF, DOCX, or TXT files."
        args_schema: type = ExtractTextInput

        def _run(self, file_path: str) -> str:
            import asyncio
            skill = DocumentProcessingSkill()
            result = asyncio.run(skill.extract_text(file_path))
            return json.dumps(result, ensure_ascii=False)

    class AnalyzeContractInput(BaseModel):
        file_path: str = Field(description="Path to contract document")

    class AnalyzeContractTool(BaseTool):
        name: str = "analyze_contract"
        description: str = "Analyze a real estate contract: extract parties, price, terms, penalties."
        args_schema: type = AnalyzeContractInput

        def _run(self, file_path: str) -> str:
            import asyncio
            skill = DocumentProcessingSkill()
            result = asyncio.run(skill.analyze_contract(file_path))
            return json.dumps(result, ensure_ascii=False)

    class ExtractPropertyDetailsInput(BaseModel):
        file_path: str = Field(description="Path to property document")

    class ExtractPropertyDetailsTool(BaseTool):
        name: str = "extract_property_from_doc"
        description: str = "Extract property details (area, rooms, price) from a document."
        args_schema: type = ExtractPropertyDetailsInput

        def _run(self, file_path: str) -> str:
            import asyncio
            skill = DocumentProcessingSkill()
            result = asyncio.run(skill.extract_property_details(file_path))
            return json.dumps(result, ensure_ascii=False)

    return [ExtractTextTool(), AnalyzeContractTool(), ExtractPropertyDetailsTool()]
