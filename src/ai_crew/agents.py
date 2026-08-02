"""
AI Agents — فريق العمل الذكي
==============================
AI agents for Egyptian real estate automation:

1. Lead Qualifier (صياد الصفقات): Filters buyer intent from posts
2. Sales Rep (مستشار المبيعات): Handles WhatsApp inbound messages
3. Copywriter (الخبير التسويقي): Generates marketing content
4. Data Collector (جامع البيانات): Crawls and extracts property data
5. Data Enricher (مier غني البيانات): Enriches data with context
6. Lead Analyst (محلل العملاء): Analyzes lead quality and scoring
7. Property Expert (خبير العقارات): Property valuation and matching
8. Market Researcher (باحث السوق): Market research and analysis
"""

import logging

from crewai import Agent

from .llm_config import get_crewai_model, is_llm_available
from .tools import (
    ContentSaveTool,
    DatabaseQueryTool,
    DataEnrichmentTool,
    DataExtractionTool,
    DataQualityTool,
    MarketResearchTool,
    PhoneValidatorTool,
    PropertySearchTool,
    WebCrawlerTool,
    WebSearchTool,
    WhatsAppCheckTool,
    WhatsAppSendTool,
    get_all_tools,
)

logger = logging.getLogger("ai_crew.agents")


def create_lead_qualifier() -> Agent:
    """Create the Lead Qualification Agent.

    This agent reads raw Facebook Group posts and:
    - Distinguishes buyers from sellers/brokers
    - Extracts property type, area, budget, bedrooms
    - Creates structured Lead data in JSON format
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="صياد الصفقات العقارية",
        goal=(
            "تحليل منشورات جروبات الفيسبوك العقارية واستخراج العملاء المحتملين. "
            "يجب تمييز منشورات الشراء الحقيقية من منشورات البائعين والسماسرة."
        ),
        backstory=(
            "أنت خبير مصري في السوق العقاري تفهم اللهجة المصرية非常好. "
            "مهمتك قراءة منشورات الفيسبوك والتمييز بين:\n"
            "- عميل بيدور على شقة/فيلا (شراء) → يتحول لـ Lead\n"
            "- سمسار أو مطور بيعمل إعلان (بيع) → يُتجاهل\n"
            "- رسالة ترحيب أو شكوى → تُتجاهل\n\n"
            "تستخرج دائماً: نوع العقار، المنطقة، الميزانية، عدد الغرف.\n"
            "ترجع النتيجة كـ JSON نظيف."
        ),
        tools=[DatabaseQueryTool(), WebSearchTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def create_sales_rep() -> Agent:
    """Create the WhatsApp Sales Agent.

    This agent handles incoming WhatsApp messages and:
    - Understands Egyptian dialect queries
    - Searches property database for matches
    - Generates natural, helpful responses
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="مستشار المبيعات العقارية",
        goal=(
            "الرد على رسائل العملاء الواردة عبر الواتساب بشكل طبيعي ومحترف. "
            "فهم طلب العميل، البحث عن العقارات المناسبة، وتقديم عرض مقنع."
        ),
        backstory=(
            "أنت مستشار مبيعات عقاري محترف في مصر. تتحدث بالعامية المصرية بشكل طبيعي. "
            "قواعدك:\n"
            "- لا تبدو كرد آلي أو بوت\n"
            "- استخدم لغة ودية ومحترفة\n"
            "- إذا عندك عقار مناسب، اعرض التفاصيل والسعر\n"
            "- إذا مفيش عقار مناسب، قول 'مشغول حالياً وهرد عليكم قريب'\n"
            "- لا تطلب معلومات حساسة (رقم بطاقة، بنك)\n"
            "- اختتم بـ CTA واضح ('عايز تعرف أكتر؟')"
        ),
        tools=[PropertySearchTool(), WhatsAppSendTool(), DatabaseQueryTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def create_copywriter() -> Agent:
    """Create the Real Estate Copywriter Agent.

    This agent generates marketing content for properties:
    - Facebook posts (long, sales-driven)
    - Instagram posts (hashtag-rich)
    - WhatsApp status (ultra-short)
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="الخبير التسويقي العقاري",
        goal=(
            "كتابة محتوى تسويقي جذاب وأصيل للعقارات. "
            "إنتاج 3 بوستات مختلفة (فيسبوك، إنستجرام، واتساب) لكل عقار."
        ),
        backstory=(
            "أنت كاتب محتوى تسويقي متخصص في العقارات في السوق المصري. "
            "أسلوبك:\n"
            "- عامية مصرية طبيعية (مش فصحى)\n"
            "- تستخدم إيموجي بشكل ذكي (مش مبالغ)\n"
            "- تضع CTA واضح في كل بوست\n"
            "- تذكر السعر والمميزات الرئيسية\n"
            "- كل بوست له ستايل مختلف:\n"
            "  * فيسبوك: طويل، تفصيلي، قصة بيعية\n"
            "  * إنستجرام: متوسط، hashtags كتير، بصري\n"
            "  * واتساب: قصير، مباشر، عاجل"
        ),
        tools=[DatabaseQueryTool(), PropertySearchTool(), WebSearchTool(), ContentSaveTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def create_powerful_agent() -> Agent:
    """Create a powerful agent with all available tools.

    This agent has access to ALL skills including:
    - Task management, Goal tracking, Kanban boards
    - Time tracking, Notes, Checklists
    - Web search, Scraping, Maps
    - Document processing, Image analysis, Translation
    - Decision matrix, Reports
    """
    model = get_crewai_model() if is_llm_available() else None
    all_tools = get_all_tools()

    return Agent(
        role="المساعد الذكي الشامل",
        goal=(
            "مساعدة المستخدم في أي مهمة تتعلق بالعقارات أو إدارة العمل. "
            "يمكنك البحث، التحليل، إنشاء التقارير، إدارة المهام، "
            "وترجمة المحتوى."
        ),
        backstory=(
            "أنت مساعد ذكي شامل متخصص في السوق العقاري المصري. "
            "لديك القدرة على:\n"
            "- البحث في الويب عن معلومات العقارات والسوق\n"
            "- تحليل العقارات ومقارنتها\n"
            "- إدارة المهام والأهداف والقوائم\n"
            "- إنشاء تقارير احترافية\n"
            "- ترجمة المحتوى بين اللغات\n"
            "- معالجة المستندات وتحليل الصور\n"
            "- حساب عوائد الاستثمار\n"
            "- تتبع الوقت والإنتاجية\n\n"
            "استخدم الأدوات المتاحة لتقديم أفضل خدمة ممكنة."
        ),
        tools=all_tools,
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )


# ===========================================================================
# NEW: Data System Agents (Phase 5)
# ===========================================================================

def create_data_collector() -> Agent:
    """Create the Data Collector Agent.

    Crawls websites, extracts property data from various sources,
    and feeds raw data into the pipeline.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="جامع البيانات العقارية",
        goal=(
            "جمع البيانات العقارية من مصادر متعددة (مواقع عقارات، واتساب، فيسبوك، صفحات ويب). "
            "استخراج البيانات المهمة: نوع العقار، المنطقة، السعر، المساحة، معلومات التواصل."
        ),
        backstory=(
            "أنت متخصص في جمع البيانات العقارية في مصر. خبرتك:\n"
            "- تصفح مواقع العقارات (OLX، عقارات، Aqarmap)\n"
            "- استخراج بيانات العقارات من الرسائل والمنشورات\n"
            "- التحقق من صحة أرقام التواصل\n"
            "- تنظيف البيانات واستخراج المعلومات المهمة\n"
            "- التأكد من جودة البيانات قبل تسليمها"
        ),
        tools=[DataExtractionTool(), WebCrawlerTool(), WhatsAppCheckTool(), WebSearchTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )


def create_data_enricher() -> Agent:
    """Create the Data Enricher Agent.

    Enriches property data with area metadata, market comparison,
    price analysis, and developer reputation.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="مier غني البيانات العقارية",
        goal=(
            "إثراء بيانات العقارات بمعلومات إضافية: متوسط أسعار المنطقة، "
            "تصنيف المطور، مقارنة الأسعار، ونقاط جودة البيانات."
        ),
        backstory=(
            "أنت محلل بيانات عقارية متخصص في سوق السادات. خبرتك:\n"
            "- حساب متوسط السعر للمتر المربع لكل منطقة\n"
            "- تصنيف المطورين العقاريين (ممتاز/جيد/مقبول)\n"
            "- مقارنة الأسعار مع السوق\n"
            "- تقييم اكتمال البيانات وجودتها\n"
            "- تقييم مدى ملاءمة العقار للمستثمر"
        ),
        tools=[DataEnrichmentTool(), DataQualityTool(), MarketResearchTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )


def create_lead_analyst() -> Agent:
    """Create the Lead Analyst Agent.

    Analyzes incoming leads, scores their quality, classifies intent,
    and recommends next actions.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="محلل العملاء المحتملين",
        goal=(
            "تحليل العملاء المحتملين وتقييم جودتهم. تصنيف نية العميل "
            "(شراء حقيقي/تصفح/سمسار)، حساب نقاط الجودة، وتحديد الإجراء التالي."
        ),
        backstory=(
            "أنت محلل بيانات متخصص في التصنيف والتقييم. خبرتك:\n"
            "- تحليل نية العميل من رسالته\n"
            "- تقييم جودة العميل بناءً على البيانات\n"
            "- تصنيف العملاء: ذهبي، فضي، برونزي، مرفوض\n"
            "- تحديد الإجراء التالي المناسب\n"
            "- اكتشاف العملاء المكررين وتجنبهم\n"
            "- تحليل اتجاهات السوق"
        ),
        tools=[DataExtractionTool(), DataQualityTool(), PhoneValidatorTool(), DatabaseQueryTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )


def create_property_expert() -> Agent:
    """Create the Property Expert Agent.

    Specializes in property valuation, matching clients to properties,
    and providing investment advice.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="خبير العقارات والاستثمار",
        goal=(
            "تقييم العقارات والمطابقة بين العملاء والعقارات المناسبة. "
            "تقديم نصائح الاستثمار العقاري في مدينة السادات."
        ),
        backstory=(
            "أنت خبير عقاري في مدينة السادات. خبرتك:\n"
            "- تقييم العقارات بناءً على الموقع والمساحة والتشطيب\n"
            "- مطابقة العميل مع العقار الأنسب\n"
            "- تحليل العائد على الاستثمار\n"
            "- معرفة المناطق المميزة في السادات\n"
            "- معرفة المطورين الموثوقين\n"
            "- التعرف على فرص الاستثمار الحقيقية"
        ),
        tools=[PropertySearchTool(), DataEnrichmentTool(), MarketResearchTool(), DatabaseQueryTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )


def create_market_researcher() -> Agent:
    """Create the Market Researcher Agent.

    Researches market trends, competitor analysis, pricing data,
    and investment opportunities in El Sadat City.
    """
    model = get_crewai_model() if is_llm_available() else None

    return Agent(
        role="باحث السوق العقاري",
        goal=(
            "بحث وتحليل اتجاهات السوق العقاري في مدينة السادات. "
            "جمع بيانات الأسعار، تحليل المنافسين، وتحديد فرص الاستثمار."
        ),
        backstory=(
            "أنت باحث سوق متخصص في العقارات في مصر. خبرتك:\n"
            "- تحليل اتجاهات الأسعار في المناطق المختلفة\n"
            "- مقارنة الأسعار مع المدن المشابهة\n"
            "- تتبع المشاريع الجديدة والتطورات\n"
            "- تحليل طلب المشترين واحتياجاتهم\n"
            "- تحديد فرص الاستثمار الناشئة\n"
            "- إعداد تقارير السوق الدورية"
        ),
        tools=[WebSearchTool(), DataEnrichmentTool(), MarketResearchTool(), DatabaseQueryTool()],
        llm=model,
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )
