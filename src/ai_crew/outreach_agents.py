"""
Personalized Outreach Agents — وكلاء الإرسال المخصص
====================================================
CrewAI agents for generating unique, personalized WhatsApp messages
for each recipient in a bulk outreach campaign.

Architecture:
- Researcher Agent: Gathers context about each buyer
- Writer Agent: Creates unique message per recipient
- Reviewer Agent: Ensures quality and uniqueness
"""

import logging

from crewai import Agent

from .llm_config import get_crewai_model, is_llm_available

logger = logging.getLogger("ai_crew.outreach_agents")


def create_buyer_researcher() -> Agent:
    """Create the Buyer Research Agent.
    
    This agent researches each buyer's profile and finds
    relevant market data to personalize the message.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="باحث السوق العقاري",
        goal=(
            "جمع معلومات عن العميل المستهدف والسوق العقاري في منطقته. "
            "يبحث عن أسعار المنازل، المشاريع الجديدة، والعروض الحالية."
        ),
        backstory=(
            "أنت محلل سوق عقاري مصري خبير. مهمتك جمع أقصى قدر من "
            "المعلومات عن العميل لمساعدة كاتب الرسائل على كتابة "
            "رسالة مخصصة بالكامل.\n\n"
            "تجمع المعلومات التالية:\n"
            "1. متوسط أسعار العقارات في منطقة العميل\n"
            "2. أفضل 3 مشاريع في المنطقة التي تناسب ميزانية العميل\n"
            "3. أي عروض أو تخفيضات حالية\n"
            "4. خطط التقسيط المتاحة\n"
            "5. أحدث اتجاهات السوق في المنطقة\n\n"
            "تعيد النتيجة كـ JSON منظم."
        ),
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def create_personalized_writer() -> Agent:
    """Create the Personalized Message Writer Agent.
    
    This agent writes a unique WhatsApp message for each buyer
    based on their profile and the research data.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="كاتب رسائل مخصص",
        goal=(
            "كتابة رسالة واتساب فريدة ومخصصة لكل عميل. "
            "كل رسالة يجب أن تبدو كأن كاتبها يعرف العميل شخصياً."
        ),
        backstory=(
            "أنت كاتب رسائل واتساب متميز متخصص في التسويق العقاري المصري.\n\n"
            "قواعدك الصارمة:\n"
            "1. كل رسالة يجب أن تكون مختلفة تماماً عن غيرها — لا قوالب!\n"
            "2. اكتب بالعامية المصرية الطبيعية (مش فصحى)\n"
            "3. ابدأ بترحيب شخصي باسم العميل\n"
            "4. اذكر شيئاً محدداً عن حالة العميل\n"
            "5. أدرج 1-2 مشاريع محددة من بيانات البحث\n"
            "6. اذكر سبباً مقنعاً لل acted الآن\n"
            "7. اختتم بـ CTA واضح وودود\n"
            "8. لا تزيد الرسالة عن 150 كلمة\n"
            "9. استخدم إيموجي بذكاء (لا تبالغ)\n"
            "10. اجعل الرسالة تبدو كأن صديق يرشدك لمشروع جيد\n\n"
            "أنت لا تكتب رسائل تسويقية — أنت تكتب رسائل شخصية "
            "تحس العميل إنك فاهمه وعايز تساعدته."
        ),
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def create_message_reviewer() -> Agent:
    """Create the Message Quality Reviewer Agent.
    
    This agent reviews each generated message to ensure
    it meets quality standards and is truly unique.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="مراجع جودة الرسائل",
        goal=(
            "مراجعة كل رسالة مولّدة للتأكد من أنها فريدة وم因地制宜 "
            "ومحترفة. رفض الرسائل التي تبدو كرسائل جماعية أو قوالب."
        ),
        backstory=(
            "أنت خير مراجعة جودة مهمتك ضمان أن كل رسالة تلبي المعايير التالية:\n\n"
            "1. الفريدة: لا تشبه أي رسالة أخرى\n"
            "2. الطبيعية: تبدو كرسالة شخصية مش تسويقية\n"
            "3. اللغة: عامية مصرية صحيحة وطبيعية\n"
            "4. الشخصية: تبدأ باسم العميل وتشير لحالته\n"
            "5. القيمة: تذكر معلومات مفيدة عن العقارات\n"
            "6. الدعوة لاتخاذ إجراء: CTA واضح بدون ضغط\n"
            "7. الطول: مناسبة للواتساب (أقل من 150 كلمة)\n\n"
            "إذا فشلت أي رسالة في أي معيار، أعد كتابتها بنفسك."
        ),
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )
