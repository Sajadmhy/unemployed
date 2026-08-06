"""Every title below is real, taken from the ingested job pool.

The hard cases all share a shape: they contain "Engineer" or "Data" but are not
engineering roles. They used to be rejected as "other"; now they route to the
family they actually belong to, so someone whose target is design or finance can
tick that family and see them.
"""
import pytest

from app.ingestion.role_family import FAMILIES, classify


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        # --- target roles: must be kept ---
        ("Software Engineer, Android", "software"),
        ("Data Engineer", "data"),
        ("Site Reliability Engineer - Dedicated Hosted Runners", "devops"),
        ("Intermediate Backend Engineer - Analytics Instrumentation", "software"),
        ("Intermediate Fullstack Engineer - Data Products", "software"),
        ("SDE Intern", "software"),
        ("Machine Learning Engineer", "ai_ml"),
        ("Data Scientist", "ai_ml"),
        # A strong signal beats the routing table.
        ("Service Delivery Engineer, SRE", "devops"),
        # --- "Engineer" but NOT software engineering ---
        ("Product Solution Engineer", "sales"),
        ("GTM Engineer - Meesho AI Services (MAS)", "sales"),
        ("Customer Success Engineer, India", "sales"),
        ("Service Delivery Engineer", "operations"),
        ("Network Delivery Engineer  1 (Pune)", "operations"),
        # --- "Data" but NOT data engineering ---
        ("Associate Manager, Data Privacy", "operations"),
        # --- business / creative / finance / HR ---
        ("Growth StratOps Associate", "operations"),
        ("Analyst, Credit Risk Management - Consumer", "finance"),
        ("Customer Experience Specialist, Stock Broking", "sales"),
        ("Strategy and Operations Associate", "operations"),
        ("Recruiting Coordinator", "hr"),
        ("Graphic Designer - Intern", "design"),
        ("Copy Writer - Intern", "content"),
        ("Associate - Content (Digest)", "content"),
        ("Equity Research Analyst (AMC)", "finance"),
        ("Video Editor Intern", "content"),
        ("Thumbnail Designer", "design"),
        ("Business Development Representative", "sales"),
        ("Internship - Content", "content"),
        # Not a role at all, so no family fits.
        ("Prospect Application for future Jobs", "other"),
        # --- families with no representative above ---
        ("Application Security Engineer", "security"),
        ("SDET - Test Automation", "qa"),
        ("Embedded Software Engineer", "hardware"),
        ("Associate Product Manager", "product"),
        ("UI/UX Designer", "design"),
        ("Research Scientist, Speech", "research"),
        ("Performance Marketing Manager", "marketing"),
    ],
)
def test_classify(title: str, expected: str) -> None:
    assert classify(title) == expected


def test_ml_platform_engineer_prefers_ai_over_software() -> None:
    """Most-specific-family-first ordering."""
    assert classify("Machine Learning Platform Engineer") == "ai_ml"


def test_every_result_is_a_known_family() -> None:
    """Preferences store family ids, so a typo here would silently hide jobs."""
    titles = [
        "Software Engineer", "Product Manager", "Recruiter", "Financial Analyst",
        "Warehouse Associate", "Brand Strategist", "Something Unclassifiable",
    ]
    for title in titles:
        assert classify(title) in (*FAMILIES, "other")
