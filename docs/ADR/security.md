# ADR 001: Evaluation of Using Azure Key Vault or Managed Identities in Infrastructure Creation

## Status

Proposed

When designing secure infrastructure for applications, two primary mechanisms for managing secrets and authentication in Azure are **Azure Key Vault** and **Managed Identities**. This document evaluates the trade-offs between these two approaches, considering their usage in both local and cloud environments.

---

## **Overview**

### **Azure Key Vault**

Azure Key Vault is a centralized cloud service for securely storing and accessing secrets, keys, and certificates. It is commonly used for managing sensitive information such as connection strings, API keys, and certificates.

### **Managed Identities**

Managed Identities provide an identity for Azure resources to authenticate to other Azure services without storing credentials in code. Managed Identities eliminate the need for developers to manage secrets manually.

---

## **Comparison of Key Vault and Managed Identities**

| **Criteria**                | **Azure Key Vault**                                                                 | **Managed Identities**                                                                |
|-----------------------------|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| **Security**                | Secrets are securely stored and accessed via RBAC or policies.                      | No secrets are stored; authentication is handled automatically by Azure.              |
| **Ease of Use**             | Requires explicit configuration to retrieve secrets.                                | Seamless integration with Azure services; no need to manage credentials.              |
| **Local Development**       | Requires tools like Azure CLI or environment variables to access secrets.           | Requires a fallback mechanism (e.g., local secrets or service principal).             |
| **Cloud Environment**       | Highly secure and centralized secret management.                                    | Best suited for cloud-native applications; eliminates secret management overhead.     |
| **Cost**                    | Additional cost for Key Vault usage (based on operations and storage).              | No additional cost; included with Azure services.                                     |
| **Flexibility**             | Can store any type of secret, including non-Azure-related secrets.                  | Limited to Azure services; cannot store arbitrary secrets.                            |
| **Performance**             | Slight latency when retrieving secrets from Key Vault.                              | Faster authentication as no external calls are required.                              |
| **Scalability**             | Scales well for managing a large number of secrets across multiple applications.    | Scales automatically with Azure resources.                                            |
| **Compliance**              | Provides audit logs and compliance features for secret access.                      | Limited compliance features; relies on Azure's built-in identity management.          |

---

## **Use Cases**

### **When to Use Azure Key Vault**

- Applications require **non-Azure secrets** (e.g., third-party API keys).
- Centralized secret management is needed across multiple environments.
- Compliance and audit requirements demand detailed logging of secret access.
- Local development environments need access to the same secrets as production.

### **When to Use Managed Identities**

- Applications are **cloud-native** and only interact with Azure services.
- Developers want to eliminate the need for secret management entirely.
- Performance is critical, and reducing latency is a priority.
- Security policies mandate avoiding the use of secrets in code or configuration.

---

## **Trade-Offs**

| **Scenario**                          | **Azure Key Vault**                                                                 | **Managed Identities**                                                                |
|---------------------------------------|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| **Local Development**                 | It can be replaced with ENV files.                                                  | Requires a fallback mechanism (e.g., service principal or local secrets).             |
| **Cloud Deployment**                  | Secure and centralized secret management.                                           | Simplifies authentication; no secrets to manage.                                      |
| **Third-Party Integrations**          | Supports storing and managing third-party secrets.                                  | Not applicable; limited to Azure services.                                            |
| **Compliance Requirements**           | Provides detailed audit logs and compliance features.                               | Limited compliance features; relies on Azure's identity management.                   |
| **Performance-Critical Applications** | Slight latency when retrieving secrets.                                             | Faster authentication as no external calls are required.                              |

---

## **Suggested Decision**

Considering that only Azure services are involved in this project then Managed Identities look like a better solution saving costs to the project, taking the need of connection strings out of the equation and also making the communication across different resources faster. Now, the suggestion for this decision is the following in two different scenarios.

### **Local Development**

- Use **environment variables** for storing secrets and access them directly from the applications.
- Alternatively, use a fallback mechanism for **Managed Identities**, such as a service principal or local secrets.

### **Cloud Environment**

- Prefer **Managed Identities** for Azure-native applications to simplify authentication and eliminate secret management.
