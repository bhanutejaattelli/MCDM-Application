"""
cloud_pricing.py — FREE cloud pricing data fetcher and normalizer.

Fetches pricing data from free, public APIs:
  - AWS Bulk Pricing API (EC2 on-demand, no auth)
  - Azure Retail Prices API (no auth)
  - GCP Cloud Billing Catalog (public, no auth)

All APIs are 100% free. No API keys required.
"""

import requests
import hashlib
import traceback
from database import (
    set_global_provider, add_update_log, utc_now, delete_all_global_providers
)


# ══════════════════════════════════════════════════════════════════════════════
# QoS ESTIMATION (deterministic, based on service name hash)
# ══════════════════════════════════════════════════════════════════════════════

def estimate_qos(service: dict) -> dict:
    """
    Estimate QoS metrics for a service since real-time QoS APIs are not free.
    Uses a deterministic hash to generate consistent, realistic values.
    """
    name = service.get("name", "unknown")
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)

    return {
        "response_time": round(50 + (h % 150), 2),          # 50–200 ms
        "throughput":    round(200 + (h >> 8) % 800, 2),     # 200–1000 req/s
        "security":      round(7 + (h >> 16) % 4, 1),       # 7–10
    }


# ══════════════════════════════════════════════════════════════════════════════
# AWS PRICING (FREE — AWS Bulk Pricing API, no auth)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_aws_pricing() -> list[dict]:
    """
    Fetch AWS EC2 pricing from the public AWS Pricing Index API.
    Uses the smaller region-specific offer file for speed.
    """
    services = []
    try:
        # Use the smaller offer index to get EC2 pricing for us-east-1
        url = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.json"
        print("[AWS] Fetching pricing data (this may take a moment)...")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        products = data.get("products", {})
        terms = data.get("terms", {}).get("OnDemand", {})

        # Focus on popular instance types
        target_instances = {
            "t3.micro", "t3.small", "t3.medium", "t3.large",
            "t3.xlarge", "t3.2xlarge",
            "m5.large", "m5.xlarge", "m5.2xlarge",
            "c5.large", "c5.xlarge", "c5.2xlarge",
            "r5.large", "r5.xlarge",
            "t2.micro", "t2.small", "t2.medium",
        }

        count = 0
        for sku, product in products.items():
            attrs = product.get("attributes", {})
            instance_type = attrs.get("instanceType", "")
            if instance_type not in target_instances:
                continue
            if attrs.get("operatingSystem") != "Linux":
                continue
            if attrs.get("tenancy") != "Shared":
                continue
            if attrs.get("preInstalledSw") != "NA":
                continue

            # Get price from terms
            price = 0.0
            sku_terms = terms.get(sku, {})
            for _, term_data in sku_terms.items():
                for _, dim in term_data.get("priceDimensions", {}).items():
                    try:
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    except (ValueError, TypeError):
                        price = 0.0
                    break
                break

            if price <= 0:
                continue

            services.append({
                "name": f"AWS EC2 {instance_type}",
                "provider": "AWS",
                "type": "Compute",
                "cost": round(price, 6),
            })
            count += 1
            if count >= 20:
                break

        print(f"[AWS] Fetched {len(services)} EC2 services.")
    except Exception as e:
        print(f"[AWS] Error fetching pricing: {e}")
        traceback.print_exc()
        # Fallback: add a few well-known AWS services with approximate pricing
        services = _aws_fallback_data()

    return services


def _aws_fallback_data() -> list[dict]:
    """Fallback AWS pricing data when API is unavailable."""
    return [
        {"name": "AWS EC2 t3.micro",   "provider": "AWS", "type": "Compute", "cost": 0.0104},
        {"name": "AWS EC2 t3.small",   "provider": "AWS", "type": "Compute", "cost": 0.0208},
        {"name": "AWS EC2 t3.medium",  "provider": "AWS", "type": "Compute", "cost": 0.0416},
        {"name": "AWS EC2 t3.large",   "provider": "AWS", "type": "Compute", "cost": 0.0832},
        {"name": "AWS EC2 m5.large",   "provider": "AWS", "type": "Compute", "cost": 0.0960},
        {"name": "AWS EC2 m5.xlarge",  "provider": "AWS", "type": "Compute", "cost": 0.1920},
        {"name": "AWS EC2 c5.large",   "provider": "AWS", "type": "Compute", "cost": 0.0850},
        {"name": "AWS EC2 c5.xlarge",  "provider": "AWS", "type": "Compute", "cost": 0.1700},
        {"name": "AWS EC2 r5.large",   "provider": "AWS", "type": "Compute", "cost": 0.1260},
        {"name": "AWS EC2 t2.micro",   "provider": "AWS", "type": "Compute", "cost": 0.0116},
        {"name": "AWS S3 Standard",    "provider": "AWS", "type": "Storage",  "cost": 0.0230},
        {"name": "AWS RDS MySQL",      "provider": "AWS", "type": "Database", "cost": 0.0170},
        {"name": "AWS Lambda",         "provider": "AWS", "type": "Compute", "cost": 0.0000},
        {"name": "AWS CloudFront",     "provider": "AWS", "type": "Network", "cost": 0.0850},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# AZURE PRICING (FREE — Azure Retail Prices API, no auth)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_azure_pricing() -> list[dict]:
    """
    Fetch Azure VM pricing from the free Azure Retail Prices API.
    https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices
    """
    services = []
    try:
        # Fetch Linux VM pricing in East US
        url = (
            "https://prices.azure.com/api/retail/prices?"
            "$filter=serviceFamily eq 'Compute' and "
            "armRegionName eq 'eastus' and "
            "priceType eq 'Consumption' and "
            "contains(productName, 'Virtual Machines') and "
            "contains(meterName, 'Spot') eq false&"
            "$top=50"
        )
        print("[Azure] Fetching pricing data...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        seen_names = set()
        for item in data.get("Items", []):
            sku_name = item.get("armSkuName", "")
            meter_name = item.get("meterName", "")

            # Skip low-priority, spot, Windows
            if "Low Priority" in meter_name or "Spot" in meter_name:
                continue
            if "Windows" in item.get("productName", ""):
                continue

            name = f"Azure VM {sku_name}"
            if name in seen_names or not sku_name:
                continue
            seen_names.add(name)

            price = item.get("retailPrice", 0)
            if price <= 0:
                continue

            services.append({
                "name": name,
                "provider": "Azure",
                "type": "Compute",
                "cost": round(price, 6),
            })
            if len(services) >= 20:
                break

        # Also fetch some storage pricing
        storage_url = (
            "https://prices.azure.com/api/retail/prices?"
            "$filter=serviceFamily eq 'Storage' and "
            "armRegionName eq 'eastus' and "
            "priceType eq 'Consumption'&"
            "$top=10"
        )
        resp2 = requests.get(storage_url, timeout=30)
        if resp2.ok:
            for item in resp2.json().get("Items", [])[:5]:
                name = f"Azure {item.get('productName', 'Storage')}"
                if name not in seen_names:
                    seen_names.add(name)
                    services.append({
                        "name": name[:60],
                        "provider": "Azure",
                        "type": "Storage",
                        "cost": round(item.get("retailPrice", 0), 6),
                    })

        print(f"[Azure] Fetched {len(services)} services.")
    except Exception as e:
        print(f"[Azure] Error fetching pricing: {e}")
        traceback.print_exc()
        services = _azure_fallback_data()

    return services


def _azure_fallback_data() -> list[dict]:
    """Fallback Azure pricing data when API is unavailable."""
    return [
        {"name": "Azure VM B1s",       "provider": "Azure", "type": "Compute",  "cost": 0.0104},
        {"name": "Azure VM B2s",       "provider": "Azure", "type": "Compute",  "cost": 0.0416},
        {"name": "Azure VM D2s v3",    "provider": "Azure", "type": "Compute",  "cost": 0.0960},
        {"name": "Azure VM D4s v3",    "provider": "Azure", "type": "Compute",  "cost": 0.1920},
        {"name": "Azure VM E2s v3",    "provider": "Azure", "type": "Compute",  "cost": 0.1260},
        {"name": "Azure VM F2s v2",    "provider": "Azure", "type": "Compute",  "cost": 0.0850},
        {"name": "Azure VM A1 v2",     "provider": "Azure", "type": "Compute",  "cost": 0.0430},
        {"name": "Azure Blob Storage", "provider": "Azure", "type": "Storage",  "cost": 0.0184},
        {"name": "Azure SQL Database", "provider": "Azure", "type": "Database", "cost": 0.0210},
        {"name": "Azure CDN",          "provider": "Azure", "type": "Network",  "cost": 0.0870},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# GCP PRICING (FREE — Public pricing page data)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_gcp_pricing() -> list[dict]:
    """
    Fetch GCP pricing from the public Cloud Pricing Calculator data endpoint.
    Falls back to hardcoded data if the API is unavailable.
    """
    services = []
    try:
        url = "https://cloudpricingcalculator.appspot.com/static/data/pricelist.json"
        print("[GCP] Fetching pricing data...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        price_list = data.get("gcp_price_list", {})

        # Extract compute engine pricing
        target_machines = [
            "e2-micro", "e2-small", "e2-medium",
            "n1-standard-1", "n1-standard-2", "n1-standard-4",
            "n2-standard-2", "n2-standard-4",
            "e2-standard-2", "e2-standard-4",
        ]

        for key, val in price_list.items():
            if not isinstance(val, dict):
                continue

            # Look for compute engine VM entries
            key_lower = key.lower()
            if "cp-computeengine-vmimage" in key_lower:
                # Get us-east1 or US pricing
                price = val.get("us", val.get("us-east1", 0))
                if isinstance(price, (int, float)) and price > 0:
                    # Extract machine type from key
                    machine_type = key.replace("CP-COMPUTEENGINE-VMIMAGE-", "").lower()
                    if machine_type in target_machines:
                        services.append({
                            "name": f"GCP CE {machine_type}",
                            "provider": "GCP",
                            "type": "Compute",
                            "cost": round(float(price), 6),
                        })

        # If we got too few from the API, supplement with fallback
        if len(services) < 5:
            services = _gcp_fallback_data()

        print(f"[GCP] Fetched {len(services)} services.")
    except Exception as e:
        print(f"[GCP] Error fetching pricing: {e}")
        traceback.print_exc()
        services = _gcp_fallback_data()

    return services


def _gcp_fallback_data() -> list[dict]:
    """Fallback GCP pricing data when API is unavailable."""
    return [
        {"name": "GCP CE e2-micro",       "provider": "GCP", "type": "Compute",  "cost": 0.0084},
        {"name": "GCP CE e2-small",        "provider": "GCP", "type": "Compute",  "cost": 0.0168},
        {"name": "GCP CE e2-medium",       "provider": "GCP", "type": "Compute",  "cost": 0.0336},
        {"name": "GCP CE n1-standard-1",   "provider": "GCP", "type": "Compute",  "cost": 0.0475},
        {"name": "GCP CE n1-standard-2",   "provider": "GCP", "type": "Compute",  "cost": 0.0950},
        {"name": "GCP CE n2-standard-2",   "provider": "GCP", "type": "Compute",  "cost": 0.0971},
        {"name": "GCP CE e2-standard-2",   "provider": "GCP", "type": "Compute",  "cost": 0.0670},
        {"name": "GCP Cloud Storage",      "provider": "GCP", "type": "Storage",  "cost": 0.0200},
        {"name": "GCP Cloud SQL MySQL",    "provider": "GCP", "type": "Database", "cost": 0.0150},
        {"name": "GCP Cloud CDN",          "provider": "GCP", "type": "Network",  "cost": 0.0800},
        {"name": "GCP Cloud Functions",    "provider": "GCP", "type": "Compute",  "cost": 0.0000},
        {"name": "GCP Cloud Run",          "provider": "GCP", "type": "Compute",  "cost": 0.0240},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# NORMALIZE + UPDATE GLOBAL DB
# ══════════════════════════════════════════════════════════════════════════════

def normalize_service(raw: dict) -> dict:
    """Normalize a raw service record into the global provider schema."""
    name = raw.get("name", "Unknown")
    qos = estimate_qos(raw)

    return {
        "name":          name,
        "provider":      raw.get("provider", "Unknown"),
        "type":          raw.get("type", "Compute"),
        "cost":          raw.get("cost", 0.0),
        "response_time": qos["response_time"],
        "throughput":    qos["throughput"],
        "security":      qos["security"],
        "last_updated":  utc_now(),
    }


def generate_provider_id(service: dict) -> str:
    """Generate a stable ID for a global provider based on its name."""
    name = service.get("name", "unknown")
    return hashlib.md5(name.encode()).hexdigest()[:16]


def update_global_db() -> dict:
    """
    Master update function: fetches all cloud pricing, normalizes, estimates QoS,
    and writes to the global_providers node in Firebase.

    Returns a summary dict with counts and status.
    """
    print("=" * 60)
    print("[UPDATE] Starting global cloud database refresh...")
    print("=" * 60)

    summary = {"aws_count": 0, "azure_count": 0, "gcp_count": 0, "status": "success", "message": ""}

    try:
        # Fetch from all providers
        aws_services = fetch_aws_pricing()
        azure_services = fetch_azure_pricing()
        gcp_services = fetch_gcp_pricing()

        summary["aws_count"] = len(aws_services)
        summary["azure_count"] = len(azure_services)
        summary["gcp_count"] = len(gcp_services)

        all_services = aws_services + azure_services + gcp_services

        if not all_services:
            summary["status"] = "error"
            summary["message"] = "No services fetched from any provider."
            add_update_log(summary)
            return summary

        # Clear existing global providers and write fresh data
        delete_all_global_providers()

        written = 0
        for raw_service in all_services:
            normalized = normalize_service(raw_service)
            provider_id = generate_provider_id(raw_service)
            set_global_provider(provider_id, normalized)
            written += 1

        summary["message"] = (
            f"Successfully updated {written} services: "
            f"{summary['aws_count']} AWS, "
            f"{summary['azure_count']} Azure, "
            f"{summary['gcp_count']} GCP."
        )
        print(f"[UPDATE] {summary['message']}")

    except Exception as e:
        summary["status"] = "error"
        summary["message"] = f"Update failed: {str(e)}"
        print(f"[UPDATE] Error: {e}")
        traceback.print_exc()

    # Log the update
    add_update_log(summary)
    return summary
