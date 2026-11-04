#!/usr/bin/env python3
"""Seed Script for Test Environment.

Loads:
  1. sample_amharic_policy.pdf into the Knowledge Store
  2. Baseline Golden Q&A records for claims and deductible inquiries
  3. National Bank of Ethiopia (NBE) regulatory source registry
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.extractor import DocumentExtractor
from app.rag.chunker import chunk_document
from app.rag.store import knowledge_store
from app.mcp.registry import regulatory_registry

GOLDEN_QA_SEEDS = [
    {
        "question": "የግል አውቶሞቢል የመጀመሪያ አደጋ ተቀናሽ ስንት ነው?",
        "answer": "በተጠቀሰው የሞተር ፖሊሲ ሰነድ መሰረት፡ የግል አውቶሞቢል የመጀመሪያ አደጋ መደበኛ ተቀናሽ 25,000 (ሃያ አምስት ሺህ) ብር ነው።",
        "section": "Article 3 - Deductibles",
        "category": "GOLDEN_QA"
    },
    {
        "question": "የሦስተኛ ወገን የካሳ ክፍያ ገደብ ለአካል ጉዳት ስንት ነው?",
        "answer": "በአዋጅ ቁጥር 799/2005 እና በፖሊሲው አንቀጽ 2 መሰረት በአንድ አደጋ ለማንኛውም ሰው የአካል ጉዳት የሚከፈለው ከፍተኛው የካሳ መጠን 500,000 (አምስት መቶ ሺህ) ብር ነው።",
        "section": "Article 2 - Liability Limits",
        "category": "GOLDEN_QA"
    },
    {
        "question": "የአደጋ ሪፖርት በስንት ሰዓት ውስጥ መደረግ አለበት?",
        "answer": "ማንኛውም አደጋ በደረሰ በ 48 ሰዓታት ውስጥ ለኢንሹራንስ ኩባንያው በስልክ ወይም በሞባይል መተግበሪያ ሪፖርት መደረግ አለበት።",
        "section": "Article 4 - Claim Reporting",
        "category": "GOLDEN_QA"
    },
    {
        "question": "ለድንገተኛ የመጀመሪያ ህክምና እርዳታ የሚሸፈነው ከፍተኛ መጠን ስንት ነው?",
        "answer": "ለድንገተኛ የመጀመሪያ እርዳታ ሕክምና ወጪ እስከ 10,000 (አስር ሺህ) ብር ወዲያውኑ ይሸፈናል።",
        "section": "Article 2 - First Aid Limit",
        "category": "GOLDEN_QA"
    },
    {
        "question": "የጭነት ተሽከርካሪ የመጀመሪያ አደጋ ተቀናሽ ሂሳብ ስንት ነው?",
        "answer": "የንግድ እና የጭነት ተሽከርካሪ የመጀመሪያ አደጋ ተቀናሽ ሂሳብ 50,000 (ሃምሳ ሺህ) ብር ነው።",
        "section": "Article 3 - Deductibles",
        "category": "GOLDEN_QA"
    }
]


def seed_all():
    print("=" * 60)
    print("InsurTech AI: Seeding Test Environment Data")
    print("=" * 60)

    # 1. Seed Amharic Policy PDF
    pdf_path = PROJECT_ROOT / "sample_amharic_policy.pdf"
    if pdf_path.exists():
        print(f"[1/3] Ingesting policy document: {pdf_path.name}")
        extraction = DocumentExtractor.extract(pdf_path.read_bytes(), pdf_path.name)
        chunks = chunk_document(
            extraction["full_text"],
            metadata={"section": "Policy Terms", "page_num": 1, "filename": pdf_path.name}
        )
        count = knowledge_store.upsert_chunks(
            chunks=chunks,
            document_id="sample_amharic_policy",
            category="POLICY",
            source_hash=extraction["source_hash"]
        )
        print(f"      -> Ingested {count} chunks into KnowledgeStore.")
    else:
        print(f"[1/3] Warning: {pdf_path} not found. Skipping PDF seeding.")

    # 2. Seed Golden QA Records
    print(f"[2/3] Seeding {len(GOLDEN_QA_SEEDS)} Golden Q&A records...")
    golden_chunks = []
    for idx, item in enumerate(GOLDEN_QA_SEEDS, 1):
        formatted_text = f"ጥያቄ: {item['question']}\nመልስ: {item['answer']}"
        golden_chunks.append({
            "content_text": formatted_text,
            "section": item["section"],
            "page_num": 1
        })
    count_qa = knowledge_store.upsert_chunks(
        chunks=golden_chunks,
        document_id="golden_qa_curated",
        category="GOLDEN_QA",
        source_hash="seed_golden_qa_v1"
    )
    print(f"      -> Seeded {count_qa} Golden Q&A chunks.")

    # 3. Seed Regulatory Source Registry
    print("[3/3] Registering National Bank of Ethiopia (NBE) regulatory portal...")
    try:
        source = regulatory_registry.register_source(
            url="https://nbe.gov.et/directives/insurance",
            name="NBE Insurance Directives Portal",
            registered_by="seed_script@insurtech.et"
        )
        print(f"      -> Registered source ID: {source['id']}")
    except Exception as e:
        print(f"      -> Registry notice: {e}")

    print("=" * 60)
    print(f"✅ Seeding Complete! Total chunks in store: {knowledge_store.total_chunks}")
    print("=" * 60)


if __name__ == "__main__":
    seed_all()
