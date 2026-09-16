// Optional demo convenience data — used only by the "Load Sample Data"
// button on the Settings page. Nothing in the pipeline (retrieval, agents,
// LLM prompts) knows this data exists; it's uploaded through the exact
// same public endpoints a real user's own documents go through.

export const SAMPLE_COMPANY_NAME = "Acme Cloud Solutions";

export const SAMPLE_KB_DOCS = [
  {
    category: "certifications",
    filename: "ISO_27001.md",
    text: "Acme Cloud Solutions holds active ISO/IEC 27001:2022 certification, audited annually by an accredited third party.",
  },
  {
    category: "security_policies",
    filename: "Encryption_Standard.md",
    text: "All customer data in transit is encrypted using TLS 1.2 or higher. All customer data at rest is encrypted using AES-256. Fleet-wide TLS 1.3 support is not yet available.",
  },
  {
    category: "support_policies",
    filename: "SLA_Policy.md",
    text: "Acme Cloud Solutions provides a 99.9% uptime SLA for Enterprise customers, with 24/7 technical support and a 30-minute critical response target. Does not currently offer a guaranteed 99.99% uptime SLA.",
  },
  {
    category: "case_studies",
    filename: "Healthcare_Case_Study.md",
    text: "Acme Cloud Solutions delivered a data platform for a regional healthcare network, including role-based access control and full audit logging. This engagement does not constitute FedRAMP authorization or certification.",
  },
  {
    category: "technical_docs",
    filename: "API_Platform.md",
    text: "The Acme platform exposes REST APIs secured with OAuth 2.0 and supports role-based access control (RBAC) down to the individual resource level.",
  },
  {
    category: "pricing",
    filename: "Pricing_Overview.md",
    text: "Enterprise pricing is quoted per seat with volume discounts starting at 50 seats. Implementation services are billed separately on a fixed-fee basis.",
  },
];

export const SAMPLE_RFP_FILENAME = "Sample_Cloud_Services_RFP.md";

export const SAMPLE_RFP_REQUIREMENTS = [
  "Vendor must have ISO 27001 certification.",
  "All customer data in transit must be encrypted using TLS 1.3 or higher.",
  "All customer data at rest must be encrypted using AES-256 or stronger.",
  "The system must enforce Role-Based Access Control (RBAC).",
  "Vendor must provide 24/7 technical support.",
  "Vendor must provide a 99.99% uptime SLA.",
  "Vendor must have FedRAMP authorization.",
  "Vendor must support REST APIs.",
  "Vendor must provide a detailed pricing structure.",
];
