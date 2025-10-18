# Internal Documents - Sample Data

This directory contains sample internal pharmaceutical research documents for testing the Internal Knowledge Agent and Bolt LLM routing.

## Sample Documents

### 1. internal-neuro-2024-01.txt
**Title**: Metformin Neuroprotective Effects in APP/PS1 Mouse Model
**Summary**: Preclinical study demonstrating tau protein reduction and cognitive improvement
**Sensitivity**: HIGH - Contains unpublished research data
**Use Case**: Testing sensitive document handling and Bolt LLM routing

### 2. internal-aging-2023-12.txt
**Title**: Longevity Effects of Metformin: Company Research Synthesis
**Summary**: Internal meta-analysis of aging research and proprietary compound screening
**Sensitivity**: HIGH - Strategic research direction
**Use Case**: Testing multi-document synthesis with sensitive flag

### 3. internal-obs-2024-03.txt
**Title**: Sildenafil in Pregnancy: Safety Assessment
**Summary**: Internal pharmacovigilance data and risk assessment
**Sensitivity**: HIGH - Regulatory-sensitive clinical data
**Use Case**: Testing PII redaction and compliance workflows

### 4. internal-strategy-2024-01.txt
**Title**: Drug Repurposing Portfolio Strategy 2024-2027
**Summary**: Strategic priorities for repurposing investments
**Sensitivity**: CONFIDENTIAL - Business strategy
**Use Case**: Testing access control and audit logging

## Testing Instructions

### Test 1: Basic Sensitive Document Handling
```json
{
  "molecule": "Metformin",
  "indications": ["Alzheimer's disease"],
  "countries": ["US"],
  "sensitive": true,
  "internal_doc_ids": ["internal-neuro-2024-01"]
}
```

**Expected Behavior**:
- Internal Knowledge Worker should process document
- LLM routing should use Bolt LLM (not OpenAI/Anthropic)
- Audit log entry should be created
- No PII should be sent to external services

### Test 2: Multi-Document Synthesis
```json
{
  "molecule": "Metformin",
  "indications": ["Alzheimer's disease", "Aging"],
  "countries": ["US", "JP"],
  "sensitive": true,
  "internal_doc_ids": ["internal-neuro-2024-01", "internal-aging-2023-12"]
}
```

**Expected Behavior**:
- Both documents should be processed
- Summary should synthesize findings from both
- All LLM calls should route to Bolt
- References should include both doc_ids

### Test 3: PII Redaction
```json
{
  "molecule": "Sildenafil",
  "indications": ["Fetal growth restriction"],
  "countries": ["US"],
  "sensitive": true,
  "internal_doc_ids": ["internal-obs-2024-03"]
}
```

**Expected Behavior**:
- Any PII in documents should be redacted
- Redaction should happen before LLM processing
- Audit log should record PII detection events

## Document Format

Internal documents should be structured as:

```
DOCUMENT ID: internal-xxx-yyyy-mm
TITLE: Full Document Title
CLASSIFICATION: HIGH/CONFIDENTIAL/RESTRICTED
AUTHOR: Research Team Name
DATE: YYYY-MM-DD

ABSTRACT:
Brief summary of findings...

KEY FINDINGS:
1. Finding one with reference [1]
2. Finding two with reference [2]

METHODOLOGY:
Description of experimental approach...

RESULTS:
Detailed results...

CONCLUSIONS:
Summary of implications...

REFERENCES:
[1] Citation 1
[2] Citation 2
```

## Security Notes

⚠️ **Important**: In production:
1. Store actual internal documents in encrypted S3 buckets
2. Implement document-level access control (RBAC)
3. Enable versioning and audit trails
4. Use separate Bolt LLM API keys for different sensitivity levels
5. Never log full document contents - only metadata
6. Implement data retention policies
7. Enable automatic PII detection and redaction
8. Use secure transfer protocols (TLS 1.3+)

## Mock Document Creation

For testing, create simple text files:

```bash
# Create a mock internal document
cat > internal-neuro-2024-01.txt << 'EOF'
DOCUMENT ID: internal-neuro-2024-01
TITLE: Metformin Neuroprotective Effects in APP/PS1 Mouse Model
CLASSIFICATION: HIGH
AUTHOR: Neuroscience Research Team
DATE: 2024-01-15

ABSTRACT:
This study investigated the neuroprotective effects of metformin in
transgenic APP/PS1 mice, a model of Alzheimer's disease. Treatment with
metformin (300 mg/kg/day) for 6 months resulted in significant reduction
in tau phosphorylation and improved performance in Morris water maze testing.

KEY FINDINGS:
1. Tau phosphorylation reduced by 42% in hippocampus (p<0.001) [1]
2. Morris water maze escape latency improved by 35% vs control (p<0.01) [2]
3. Amyloid plaque burden reduced by 28% in cortex (p<0.05) [3]
4. No significant adverse effects observed on body weight or glucose levels [4]

METHODOLOGY:
APP/PS1 transgenic mice (n=24 per group) received metformin or vehicle
starting at 6 months of age. Behavioral testing conducted monthly.
Histological analysis performed at study termination.

RESULTS:
Detailed immunohistochemistry revealed significant reduction in
phosphorylated tau (AT8 antibody) in CA1 region of hippocampus.
Western blot analysis confirmed decreased p-tau/total-tau ratio.
Behavioral improvements correlated with biochemical markers.

CONCLUSIONS:
These preclinical findings support further investigation of metformin
as a potential disease-modifying therapy for Alzheimer's disease.
The mechanism appears to involve AMPK activation and downstream effects
on tau phosphorylation. Human trials are warranted.

REFERENCES:
[1] Internal histology data, slides NH-2024-001 to NH-2024-048
[2] Behavioral testing data, database entry BT-2024-0156
[3] Plaque quantification analysis, imaging dataset IM-2024-0089
[4] Safety monitoring data, veterinary reports VM-2024-Q1
EOF
```

## Integration Testing

Test the complete pipeline:

```python
# Test script example
def test_internal_document_processing():
    query = {
        "molecule": "Metformin",
        "indications": ["Alzheimer's disease"],
        "sensitive": True,
        "internal_doc_ids": ["internal-neuro-2024-01"]
    }

    # Submit query
    response = client.post("/api/v1/master/query", json=query)
    query_id = response.json()["query_id"]

    # Wait for completion
    status = wait_for_completion(query_id)

    # Verify LLM routing
    assert status["llm_provider"] == "bolt"

    # Verify references include internal doc
    references = status["summary"]["references"]
    assert any("internal-neuro-2024-01" in ref["doc_id"] for ref in references)

    # Verify no PII leaked
    audit_logs = get_audit_logs(query_id)
    assert all(log["external_api"] != "openai" for log in audit_logs if log["sensitive"])
```

---

**Remember**: These are mock documents for testing. In production, implement proper document management, encryption, and access control.
