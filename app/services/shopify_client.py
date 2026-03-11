"""
ReturnShield AI — Shopify GraphQL Client

Async client for interacting with the Shopify Admin GraphQL API.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

SHOPIFY_API_VERSION = "2024-10"


class ShopifyClient:
    """Async client for the Shopify Admin API."""

    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}"
        self.graphql_url = f"{self.base_url}/graphql.json"

    async def graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query against the Shopify Admin API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.graphql_url,
                headers={
                    "X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables or {}},
            )

        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            logger.error(f"Shopify GraphQL errors: {data['errors']}")
            raise Exception(f"Shopify API error: {data['errors']}")

        return data.get("data", {})

    async def get_order(self, order_id: int) -> dict:
        """Fetch a single order by ID."""
        query = """
        query getOrder($id: ID!) {
            order(id: $id) {
                id
                name
                email
                totalPriceSet { shopMoney { amount currencyCode } }
                lineItems(first: 50) {
                    edges {
                        node {
                            id
                            title
                            quantity
                            variant { id title sku }
                            product { id title }
                        }
                    }
                }
                shippingAddress { city provinceCode countryCode }
                fulfillments { status }
                createdAt
            }
        }
        """
        gid = f"gid://shopify/Order/{order_id}"
        data = await self.graphql(query, {"id": gid})
        return data.get("order", {})

    async def get_product(self, product_id: int) -> dict:
        """Fetch a single product by ID."""
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                productType
                variants(first: 100) {
                    edges {
                        node {
                            id
                            title
                            sku
                            selectedOptions { name value }
                        }
                    }
                }
                tags
            }
        }
        """
        gid = f"gid://shopify/Product/{product_id}"
        data = await self.graphql(query, {"id": gid})
        return data.get("product", {})

    async def create_draft_order(self, line_items: list[dict], customer_email: str) -> dict:
        """Create a draft order for an exchange."""
        query = """
        mutation draftOrderCreate($input: DraftOrderInput!) {
            draftOrderCreate(input: $input) {
                draftOrder {
                    id
                    name
                    totalPriceSet { shopMoney { amount currencyCode } }
                }
                userErrors { field message }
            }
        }
        """
        input_data = {
            "email": customer_email,
            "lineItems": line_items,
            "note": "Exchange order created by ReturnShield AI",
        }
        data = await self.graphql(query, {"input": input_data})
        return data.get("draftOrderCreate", {})

    async def add_order_tags(self, order_id: int, tags: list[str]) -> dict:
        """Add tags to an order (e.g., 'high-return-risk')."""
        query = """
        mutation tagsAdd($id: ID!, $tags: [String!]!) {
            tagsAdd(id: $id, tags: $tags) {
                node { ... on Order { id tags } }
                userErrors { field message }
            }
        }
        """
        gid = f"gid://shopify/Order/{order_id}"
        data = await self.graphql(query, {"id": gid, "tags": tags})
        return data.get("tagsAdd", {})
    async def get_historical_orders(self, first: int = 250, query: str = "") -> list[dict]:
        """Fetch historical orders for ML training."""
        query_str = """
        query getHistoricalOrders($first: Int!, $query: String) {
            orders(first: $first, query: $query) {
                edges {
                    node {
                        id
                        name
                        totalPriceSet { shopMoney { amount } }
                        lineItems(first: 20) {
                            edges {
                                node {
                                    id
                                    product { id productType }
                                    variant { id }
                                    quantity
                                }
                            }
                        }
                        customer { id }
                        createdAt
                        displayFinancialStatus
                        displayFulfillmentStatus
                        totalRefundedSet { shopMoney { amount } }
                    }
                }
            }
        }
        """
        data = await self.graphql(query_str, {"first": first, "query": query})
        return [edge["node"] for edge in data.get("orders", {}).get("edges", [])]
