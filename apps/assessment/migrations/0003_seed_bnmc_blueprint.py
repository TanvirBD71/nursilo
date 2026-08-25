"""
Seed the BNMC Comprehensive Registration Examination Blueprint (November 2018).

Data is transcribed EXACTLY from the authoritative source PDF
("Examination Blue Print.pdf", BNMC, November 2018), Tables 1–6:
  * Table 1 — five competency categories + their question allocation (total 100)
  * Tables 2–6 — the 40 competency statements with per-competency question counts
  * Cognitive skill levels — Recall 50% / Understanding 25% / Application 25%

Nothing here is invented: categories, competency wording, weights, and counts
are taken verbatim from the blueprint. This is a data/config representation
(UNIT-11), NOT a hard-coded runtime view, and is never asserted to be the latest
BNMC revision.
"""
from django.db import migrations

BLUEPRINT_CODE = "BNMC_2018"

CATEGORIES = [
    # (code, name, percent, question_count, sort_order)
    ("NURSING_PROCESS", "Nursing Process", 15, 15, 1),
    ("FUNDAMENTALS", "Fundamentals of Nursing", 30, 30, 2),
    ("GENERAL_NURSING_CARE", "General Nursing Care", 33, 33, 3),
    ("COMMUNICATION", "Communication", 10, 10, 4),
    ("PROFESSIONALISM_LEADERSHIP", "Nursing Professionalism and Leadership", 12, 12, 5),
]

# (category_code, number, text, percent, question_count)
COMPETENCIES = [
    # Table 2 — Nursing Process (15)
    ("NURSING_PROCESS", 1, "Performs a comprehensive, systematic and holistic health assessment of the patient/client.", 4, 4),
    ("NURSING_PROCESS", 2, "Identifies the patient's/client's needs/expectations/responses to actual health programs.", 3, 3),
    ("NURSING_PROCESS", 3, "Formulates a plan of care in collaboration with the healthcare team.", 3, 3),
    ("NURSING_PROCESS", 4, "Implements a nursing care plan in a timely manner.", 2, 2),
    ("NURSING_PROCESS", 5, "Evaluates and modifies the plan of care to meet expected outcomes.", 2, 2),
    ("NURSING_PROCESS", 6, "Documents appropriately.", 1, 1),
    # Table 3 — Fundamentals of Nursing (30)
    ("FUNDAMENTALS", 7, "Applies knowledge from health sciences and related disciplines in caring for patients/clients.", 2, 2),
    ("FUNDAMENTALS", 8, "Provides nursing care to patients/clients of all age groups, both sexes, all races, religions and ethnic groups.", 3, 3),
    ("FUNDAMENTALS", 9, "Provides health information, education and counselling appropriate to the needs of the patients, clients and families.", 2, 2),
    ("FUNDAMENTALS", 10, "Receives patients/clients properly and provides necessary support to patients/clients transitioning to other units in the hospital and to other care facilities.", 1, 1),
    ("FUNDAMENTALS", 11, "Safely administers drugs and medications in oral and parenteral routes.", 4, 4),
    ("FUNDAMENTALS", 12, "Responds appropriately to alterations of a patient/client's cardio-pulmonary functioning and monitors patient's/client's respiratory function.", 3, 3),
    ("FUNDAMENTALS", 13, "Supports basic physiological systems and mobility needs.", 3, 3),
    ("FUNDAMENTALS", 14, "Provides pre- and post-operative care appropriately to acute or chronically ill patients/clients undergoing major or minor surgery.", 3, 3),
    ("FUNDAMENTALS", 15, "Works with physicians in performing invasive diagnostic procedures.", 1, 1),
    ("FUNDAMENTALS", 16, "Uses a variety of techniques to manage patient's/client's pain.", 3, 3),
    ("FUNDAMENTALS", 17, "Response effectively to rapid change in the patient's/client's health status.", 2, 2),
    ("FUNDAMENTALS", 18, "Performs infection control measures appropriately in the hospital and in the community.", 3, 3),
    # Table 4 — General Nursing Care (33)
    ("GENERAL_NURSING_CARE", 19, "Provides appropriate nursing care to adults with acute and chronic health conditions.", 3, 3),
    ("GENERAL_NURSING_CARE", 20, "Provides appropriate nursing care to infants and children with acute and chronic health conditions.", 3, 3),
    ("GENERAL_NURSING_CARE", 21, "Provides appropriate nursing care to the elderly with acute and chronic health conditions.", 4, 4),
    ("GENERAL_NURSING_CARE", 22, "Provides palliative and end-of-life nursing care for patients/clients at the end stage of life.", 1, 1),
    ("GENERAL_NURSING_CARE", 23, "Provides ante-natal midwifery services to patients/clients.", 3, 3),
    ("GENERAL_NURSING_CARE", 24, "Provides holistic care to the pregnant woman during labour and delivery.", 3, 3),
    ("GENERAL_NURSING_CARE", 25, "Provides appropriate care to the newborn infant following delivery.", 3, 3),
    ("GENERAL_NURSING_CARE", 26, "Provides appropriate postpartum care to the mother.", 3, 3),
    ("GENERAL_NURSING_CARE", 27, "Provides appropriate care to the woman presenting with an incomplete, complete, habitual, or septic abortion.", 2, 2),
    ("GENERAL_NURSING_CARE", 28, "Assesses the health status of the family and the community.", 1, 1),
    ("GENERAL_NURSING_CARE", 29, "Promotes health and prevents disease among individuals, families, and communities.", 2, 2),
    ("GENERAL_NURSING_CARE", 30, "Provides support and determine strategies for individuals in the community managing a chronic disease or health issue.", 2, 2),
    ("GENERAL_NURSING_CARE", 31, "Provides safe and compassionate care to patients/clients experiencing a mental health issue or illness.", 3, 3),
    # Table 5 — Communication (10)
    ("COMMUNICATION", 32, "Uses the key elements of effective communication in building interpersonal relationships.", 5, 5),
    ("COMMUNICATION", 33, "Initiates, develops and terminates a therapeutic relationship with the patient/clients and family.", 2, 2),
    ("COMMUNICATION", 34, "Establishes and maintains constructive working relationship with nursing and other colleagues.", 2, 2),
    ("COMMUNICATION", 35, "Communicates with patients/clients and other members of the health care team through clear and concise verbal/non-verbal/written communication.", 1, 1),
    # Table 6 — Nursing Professionalism and Leadership (12)
    ("PROFESSIONALISM_LEADERSHIP", 36, "Performs duties expected in the Scope of Practice and complies with the Code of Ethics as established by the BNMC.", 3, 3),
    ("PROFESSIONALISM_LEADERSHIP", 37, "Is accountable for his/her actions and to her immediate supervisor, employers, and to the general public.", 3, 3),
    ("PROFESSIONALISM_LEADERSHIP", 38, "Provides ethical and processional nursing care to patients/clients.", 4, 4),
    ("PROFESSIONALISM_LEADERSHIP", 39, "Manages time effectively in providing patient/client care.", 1, 1),
    ("PROFESSIONALISM_LEADERSHIP", 40, "Follows protocols during an emergency situation.", 1, 1),
]

COGNITIVE_ALLOCATIONS = [
    # (cognitive_level, percent, sort_order)
    ("recall", 50, 1),
    ("understanding", 25, 2),
    ("application", 25, 3),
]


def seed_blueprint(apps, schema_editor):
    ExamBlueprint = apps.get_model("assessment", "ExamBlueprint")
    BlueprintCategory = apps.get_model("assessment", "BlueprintCategory")
    BlueprintCompetency = apps.get_model("assessment", "BlueprintCompetency")
    BlueprintCognitiveAllocation = apps.get_model(
        "assessment", "BlueprintCognitiveAllocation"
    )

    blueprint, _ = ExamBlueprint.objects.get_or_create(
        code=BLUEPRINT_CODE,
        defaults={
            "name": "BNMC Comprehensive Registration Examination Blueprint",
            "version_label": "November 2018",
            "source_authority": "Bangladesh Nursing and Midwifery Council (BNMC)",
            "total_questions": 100,
            "is_active": True,
            "notes": (
                "Transcribed verbatim from the BNMC Comprehensive Registration "
                "Examination Blueprint (November 2018), Tables 1-6. Not asserted to "
                "be the latest BNMC revision."
            ),
        },
    )

    category_by_code = {}
    for code, name, percent, count, sort_order in CATEGORIES:
        category, _ = BlueprintCategory.objects.get_or_create(
            blueprint=blueprint,
            code=code,
            defaults={
                "name": name,
                "percent": percent,
                "question_count": count,
                "sort_order": sort_order,
            },
        )
        category_by_code[code] = category

    for cat_code, number, text, percent, count in COMPETENCIES:
        category = category_by_code[cat_code]
        BlueprintCompetency.objects.get_or_create(
            category=category,
            code=f"C{number}",
            defaults={
                "number": number,
                "text": text,
                "percent": percent,
                "question_count": count,
                "sort_order": number,
            },
        )

    for level, percent, sort_order in COGNITIVE_ALLOCATIONS:
        BlueprintCognitiveAllocation.objects.get_or_create(
            blueprint=blueprint,
            cognitive_level=level,
            defaults={"percent": percent, "sort_order": sort_order},
        )


def unseed_blueprint(apps, schema_editor):
    ExamBlueprint = apps.get_model("assessment", "ExamBlueprint")
    ExamBlueprint.objects.filter(code=BLUEPRINT_CODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0002_blueprintcategory_attemptitem_score_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_blueprint, unseed_blueprint),
    ]
