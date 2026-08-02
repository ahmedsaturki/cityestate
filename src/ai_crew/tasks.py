"""
AI Tasks — مهام فريق العمل الذكي
==================================
Task definitions for each CrewAI agent.
Each task has a clear description, expected output, and agent assignment.
"""

from crewai import Task

from .agents import (
    create_copywriter,
    create_data_collector,
    create_data_enricher,
    create_lead_analyst,
    create_lead_qualifier,
    create_market_researcher,
    create_property_expert,
    create_sales_rep,
)


def create_lead_qualification_task(posts_text: str) -> Task:
    """Create a task for qualifying Facebook Group posts.

    Args:
        posts_text: Raw scraped posts concatenated

    Returns:
        CrewAI Task object
    """
    agent = create_lead_qualifier()

    return Task(
        description=(
            f"حلل المنشورات التالية من جروبات الفيسبوك العقارية واستخرج العملاء المحتملين.\n\n"
            f"**المنشورات:**\n{posts_text}\n\n"
            "**تعليمات:**\n"
            "1. اقرأ كل منشور بعناية\n"
            "2. قرر: هل هذا عميل يبحث عن عقار (شراء)؟ أم بائع/سمسار؟\n"
            "3. إذا كان عميل → استخرج: نوع العقار، المنطقة، الميزانية، عدد الغرف\n"
            "4. إذا كان بائع أو رسالة ترحيب → تجاهل\n"
            "5. رجع النتيجة كـ JSON array"
        ),
        expected_output=(
            'JSON array بالشكل:\n'
            '[\n'
            '  {\n'
            '    "is_buyer": true,\n'
            '    "property_type": "apartment",\n'
            '    "area": "Sheikh Zayed",\n'
            '    "budget_max": 3000000,\n'
            '    "bedrooms": 3,\n'
            '    "summary": "عميل يبحث عن شقة 3 غرف في الشيخ زايد بميزانية 3 مليون"\n'
            '  }\n'
            ']\n'
            'إذا لم يتم العثور على عملاء، أرجع: []'
        ),
        agent=agent,
    )


def create_whatsapp_reply_task(
    message: str, sender_name: str, available_properties: str
) -> Task:
    """Create a task for replying to WhatsApp messages.

    Args:
        message: The incoming WhatsApp message
        sender_name: Name of the sender
        available_properties: JSON string of matching properties

    Returns:
        CrewAI Task object
    """
    agent = create_sales_rep()

    return Task(
        description=(
            f"رد على رسالة واتساب واردة من عميل.\n\n"
            f"**الرسالة:** {message}\n"
            f"**اسم العميل:** {sender_name}\n"
            f"**العقارات المتاحة:** {available_properties}\n\n"
            "**تعليمات:**\n"
            "1. افهم طلب العميل من رسالته\n"
            "2. راجع العقارات المتاحة\n"
            "3. إذا يوجد عقار مناسب → قدّم عرض قصير مع السعر والمميزات\n"
            "4. إذا لا يوجد مناسب → اعتذر بلطف وقول هترد عليه لاحقاً\n"
            "5. الرد يكون بالعامية المصريةطبيعية\n"
            "6. لا تبدو كبوت — كن مثل مستشار مبيعات محترف\n"
            "7. اختتم بـ CTA واضح"
        ),
        expected_output=(
            "رسالة واتساب جاهزة للإرسال بالعامية المصرية. "
            "لا تزيد عن 3 سطور. تبدأ بترحيب وتنتهي بـ CTA."
        ),
        agent=agent,
    )


def create_content_generation_task(property_data: str, channel: str = "all") -> Task:
    """Create a task for generating marketing content.

    Args:
        property_data: JSON string with property details
        channel: Target channel (facebook, instagram, whatsapp, or all)

    Returns:
        CrewAI Task object
    """
    agent = create_copywriter()

    channel_instructions = {
        "facebook": (
            "بوست فيسبوك طويل (200-350 كلمة): "
            "ابدأ بـ hook قوي، اذكر التفاصيل والمميزات، "
            "السعر، وختم بـ CTA. استخدم إيموجي بذكاء."
        ),
        "instagram": (
            "بوست إنستجرام متوسط (150-250 كلمة): "
            "ابدأ بـ caption جذاب، استخدم 10-15 hashtags شائعة في العقارات المصرية. "
            "ركّز على الشكل البصري والمشاعر."
        ),
        "whatsapp": (
            "رسالة واتساب قصيرة (50-100 كلمة): "
            "مباشرة وسريعة. السعر والميزة الرئيسية + CTA. "
            "بدون hashtags."
        ),
    }

    if channel == "all":
        channels_text = "\n".join(
            f"- **{ch.upper()}**: {desc}"
            for ch, desc in channel_instructions.items()
        )
    else:
        channels_text = f"- **{channel.upper()}**: {channel_instructions.get(channel, channel_instructions['facebook'])}"

    return Task(
        description=(
            f"اكتب محتوى تسويقي للعقار التالي:\n\n"
            f"**بيانات العقار:**\n{property_data}\n\n"
            f"**القنوات المطلوبة:**\n{channels_text}\n\n"
            "**تعليمات:**\n"
            "1. كل بوست له ستايل مختلف حسب القناة\n"
            "2. استخدم عامية مصرية طبيعية\n"
            "3. لا تستخدم قوالب ثابتة — كن إبداعياً\n"
            "4. ضع إيموجي بذكاء (مش مبالغ)\n"
            "5. كل بوست يجب أن يحتوي CTA واضح\n"
            "6. اذكر السعر والمميزات الرئيسية"
        ),
        expected_output=(
            "3 بوستات جاهزة للنشر:\n\n"
            "1. **فيسبوك:** بوست كامل\n"
            "2. **إنستجرام:** بوست + hashtags\n"
            "3. **واتساب:** رسالة قصيرة\n\n"
            "كل بوست منفصل بعنوان واضح."
        ),
        agent=agent,
    )


# ===========================================================================
# NEW: Data System Tasks (Phase 5)
# ===========================================================================

def create_data_collection_task(source: str, raw_data: str) -> Task:
    """Create a task for collecting and extracting data from a source.

    Args:
        source: Data source type ('whatsapp', 'facebook', 'web', 'json')
        raw_data: Raw text/data to extract from

    Returns:
        CrewAI Task object
    """
    agent = create_data_collector()

    return Task(
        description=(
            f"استخراج البيانات العقارية من مصدر `{source}`.\n\n"
            f"**البيانات الخام:**\n{raw_data[:3000]}\n\n"
            "**تعليمات:**\n"
            "1. استخدم أداة الاستخراج المناسبة لنوع المصدر\n"
            "2. استخرج: نوع العقار، المنطقة، السعر، المساحة، الغرف، رقم التواصل\n"
            "3. تحقق من صحة الأرقام (هاتف مصري: 01X-XXXX-XXXX)\n"
            "4. رجع البيانات كـ JSON منظّم\n"
            "5. إذا لم تجد بيانات كافية، أرجع: {\"error\": \"insufficient data\"}"
        ),
        expected_output=(
            'JSON object بالشكل:\n'
            '{\n'
            '  "source": "whatsapp|facebook|web",\n'
            '  "extracted_data": {\n'
            '    "property_type": "apartment|villa|land|commercial",\n'
            '    "area": "المنطقة",\n'
            '    "price": 1500000,\n'
            '    "area_sqm": 150,\n'
            '    "bedrooms": 3,\n'
            '    "phone": "+20112345678",\n'
            '    "client_name": "الاسم",\n'
            '    "intent": "buying|inquiry|selling",\n'
            '    "confidence": 0.85\n'
            '  }\n'
            '}'
        ),
        agent=agent,
    )


def create_data_enrichment_task(property_data: str) -> Task:
    """Create a task for enriching property data.

    Args:
        property_data: JSON string of extracted property data

    Returns:
        CrewAI Task object
    """
    agent = create_data_enricher()

    return Task(
        description=(
            f"إثراء بيانات العقار بالمعلومات الإضافية.\n\n"
            f"**بيانات العقار:**\n{property_data[:2000]}\n\n"
            "**تعليمات:**\n"
            "1. حساب السعر للمتر المربع\n"
            "2. مقارنة السعر مع متوسط أسعار المنطقة\n"
            "3. تصنيف المطور إذا وجد\n"
            "4. تقييم جودة البيانات\n"
            "5. تحديد ما إذا كان العقار ممتاز (premium) أم لا\n"
            "6. رجع البيانات المُثراة كـ JSON"
        ),
        expected_output=(
            'JSON object بالشكل:\n'
            '{\n'
            '  "enriched_data": {\n'
            '    "price_per_sqm": 10000,\n'
            '    "area_avg_price": 12000,\n'
            '    "price_comparison": "below_market|at_market|above_market",\n'
            '    "developer_reputation": "excellent|good|average|unknown",\n'
            '    "is_premium": true,\n'
            '    "premium_score": 85,\n'
            '    "data_quality": {\n'
            '      "completeness": 0.9,\n'
            '      "score": 80,\n'
            '      "tier": "good"\n'
            '    }\n'
            '  }\n'
            '}'
        ),
        agent=agent,
    )


def create_lead_analysis_task(lead_data: str) -> Task:
    """Create a task for analyzing and scoring a lead.

    Args:
        lead_data: JSON string of lead/extracted data

    Returns:
        CrewAI Task object
    """
    agent = create_lead_analyst()

    return Task(
        description=(
            f"تحليل وتصنيف العميل المحتمل.\n\n"
            f"**بيانات العميل:**\n{lead_data[:2000]}\n\n"
            "**تعليمات:**\n"
            "1. حدد نية العميل: شراء حقيقي / تصفح / سمسار\n"
            "2. قيّم جودة العميل (نقاط من 100)\n"
            "3. صنّف العميل: ذهبي (≥80) / فضي (60-79) / برونزي (40-59) / مرفوض (<40)\n"
            "4. حدد الإجراء التالي: رد فوري / تأكيد هوية / طلب معلومات / رفض\n"
            "5. إذا كان العميل مكرر، حدد ذلك\n"
            "6. رجع التحليل كـ JSON"
        ),
        expected_output=(
            'JSON object بالشكل:\n'
            '{\n'
            '  "analysis": {\n'
            '    "intent": "buying|inquiry|selling|spam",\n'
            '    "intent_confidence": 0.9,\n'
            '    "score": 75,\n'
            '    "tier": "gold",\n'
            '    "quality": "high",\n'
            '    "action": "reply_with_properties|verify_identity|request_info|reject",\n'
            '    "reasons": ["_reason1", "_reason2"],\n'
            '    "is_duplicate": false\n'
            '  }\n'
            '}'
        ),
        agent=agent,
    )


def create_property_matching_task(client_data: str) -> Task:
    """Create a task for matching a client to properties.

    Args:
        client_data: JSON string of client requirements

    Returns:
        CrewAI Task object
    """
    agent = create_property_expert()

    return Task(
        description=(
            f"مطابقة العميل مع العقارات المناسبة.\n\n"
            f"**بيانات العميل:**\n{client_data[:2000]}\n\n"
            "**تعليمات:**\n"
            "1. ابحث عن العقارات المناسبة في قاعدة البيانات\n"
            "2. قارن متطلبات العميل مع العقارات المتاحة\n"
            "3. رتّب النتائج حسب الأفضلية\n"
            "4. قدّم أقصى 3 عقارات مناسبة\n"
            "5. اذكر السعر والمميزات لكل عقار\n"
            "6. رجع النتائج كـ JSON"
        ),
        expected_output=(
            'JSON array بالشكل:\n'
            '[\n'
            '  {\n'
            '    "property_id": 123,\n'
            '    "name": "سمارت فيلا ريزيدنس",\n'
            '    "match_score": 95,\n'
            '    "price": 3500000,\n'
            '    "price_per_sqm": 25000,\n'
            '    "area_sqm": 140,\n'
            '    "bedrooms": 3,\n'
            '    "features": ["مسبح", "أمن", "جراج"]\n'
            '  }\n'
            ']\n'
            'إذا لم يُوجد عقار مناسب، أرجع: []'
        ),
        agent=agent,
    )


def create_market_research_task(area: str | None = None) -> Task:
    """Create a task for market research.

    Args:
        area: Specific area to research (optional)

    Returns:
        CrewAI Task object
    """
    agent = create_market_researcher()
    area_filter = f" في منطقة {area}" if area else " في مدينة السادات بشكل عام"

    return Task(
        description=(
            f"إجراء بحث سوق للعقارات{area_filter}.\n\n"
            "**تعليمات:**\n"
            "1. ابحث عن أحدث بيانات الأسعار في المنطقة\n"
            "2. حدد المشاريع الجديدة والتطورات\n"
            "3. قارن الأسعار مع المناطق المشابهة\n"
            "4. حدد فرص الاستثمار الناشئة\n"
            "5. قيّم قوة الطلب والعرض\n"
            "6. رجع البحث كـ JSON"
        ),
        expected_output=(
            'JSON object بالشكل:\n'
            '{\n'
            '  "market_report": {\n'
            '    "area": "المنطقة",\n'
            '    "avg_price_per_sqm": 12000,\n'
            '    "price_trend": "increasing|stable|decreasing",\n'
            '    "new_projects": ["مشروع1", "مشروع2"],\n'
            '    "investment_opportunities": ["فرصة1"],\n'
            '    "demand_level": "high|medium|low",\n'
            '    "competition_level": "high|medium|low"\n'
            '  }\n'
            '}'
        ),
        agent=agent,
    )
