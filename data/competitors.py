"""Veeva Systems competitive landscape knowledge base."""

DIRECT_COMPETITOR_NAMES = [
    "salesforce life sciences", "iqvia", "medidata", "oracle health sciences",
    "opentext documentum", "model n", "benchling", "dotmatics", "certinia",
]
INDIRECT_COMPETITOR_NAMES = [
    "microsoft dynamics", "palantir", "unlearn.ai", "deep 6 ai",
    "saama technologies", "box life sciences", "egnyte",
]
COMPETITOR_DOMAIN_KEYWORDS = [
    "pharma CRM", "life sciences CRM", "regulatory information management",
    "clinical data management", "electronic trial master file", "eTMF",
    "clinical trial management", "CTMS", "quality management system", "QMS",
    "promotional content management", "medical legal review", "MLR",
    "healthcare professional data", "HCP data", "pharma software",
    "biotech software platform", "drug development software",
    "regulatory submission", "electronic data capture", "EDC",
]
VEEVA_CONTEXT = """
ABOUT VEEVA SYSTEMS (VEEV):
Products: Veeva CRM (moving to Vault CRM), Vault RIM, Vault QualityDocs, Vault PromoMats,
Vault eTMF, Vault CTMS, Vault CDMS, Veeva Network, Veeva OpenData, Veeva Link.
Business model: SaaS per-user and per-module. Market position: dominant in pharma CRM and regulatory content.

DIRECT COMPETITORS: Salesforce Life Sciences Cloud, IQVIA OCE, Medidata (Dassault), Oracle Health Sciences,
OpenText Documentum, Model N, Benchling, Dotmatics.
INDIRECT: Microsoft Cloud for Life Sciences, Palantir pharma, Unlearn.AI, Deep 6 AI, Saama Technologies.
EMERGING THREATS: Benchling expanding from lab to commercial, AI-native pharma CRM startups,
Microsoft Cloud for Life Sciences bundled offering.

HIGH relevance: direct competitor funding/product/major pharma win; large pharma migrating from Veeva;
AI-native platform gaining clinical or regulatory traction; Salesforce/Microsoft life sciences launch.
MEDIUM relevance: life sciences SaaS raises Series B+; pharma tech partnership; VC thesis on pharma tech.
LOW (exclude): consumer health apps, pre-seed under $5M, medical devices with no software angle.
"""
