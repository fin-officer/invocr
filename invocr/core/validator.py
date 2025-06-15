"""
Data validation module for InvOCR
Validates extracted invoice data and provides quality metrics
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error"""

    field: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    value: Any = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation result with errors and quality score"""

    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    errors: List[ValidationError]
    warnings: List[ValidationError]
    suggestions: List[str]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class InvoiceValidator:
    """Comprehensive invoice data validator"""

    def __init__(self):
        self.required_fields = [
            "document_number",
            "document_date",
            "seller",
            "buyer",
            "items",
            "totals",
        ]

        self.required_seller_fields = ["name"]
        self.required_buyer_fields = ["name"]
        self.required_item_fields = [
            "description",
            "quantity",
            "unit_price",
            "total_price",
        ]
        self.required_totals_fields = ["total"]

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive validation of invoice data

        Args:
            data: Invoice data dictionary

        Returns:
            ValidationResult with errors, warnings and quality score
        """
        errors = []
        warnings = []
        suggestions = []

        # Basic structure validation
        structure_errors = self._validate_structure(data)
        errors.extend(structure_errors)

        # Field-specific validations
        if "document_number" in data:
            doc_errors, doc_warnings = self._validate_document_number(
                data["document_number"]
            )
            errors.extend(doc_errors)
            warnings.extend(doc_warnings)

        if "document_date" in data:
            date_errors, date_warnings = self._validate_dates(data)
            errors.extend(date_errors)
            warnings.extend(date_warnings)

        if "seller" in data:
            seller_errors, seller_warnings = self._validate_party(
                data["seller"], "seller"
            )
            errors.extend(seller_errors)
            warnings.extend(seller_warnings)

        if "buyer" in data:
            buyer_errors, buyer_warnings = self._validate_party(data["buyer"], "buyer")
            errors.extend(buyer_errors)
            warnings.extend(buyer_warnings)

        if "items" in data:
            items_errors, items_warnings, items_suggestions = self._validate_items(
                data["items"]
            )
            errors.extend(items_errors)
            warnings.extend(items_warnings)
            suggestions.extend(items_suggestions)

        if "totals" in data:
            totals_errors, totals_warnings = self._validate_totals(
                data["totals"], data.get("items", [])
            )
            errors.extend(totals_errors)
            warnings.extend(totals_warnings)

        # Cross-field validations
        cross_errors, cross_warnings = self._validate_cross_fields(data)
        errors.extend(cross_errors)
        warnings.extend(cross_warnings)

        # Calculate quality score
        quality_score = self._calculate_quality_score(data, errors, warnings)

        # Generate suggestions
        suggestions.extend(self._generate_suggestions(data, errors, warnings))

        return ValidationResult(
            is_valid=len(errors) == 0,
            quality_score=quality_score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _validate_structure(self, data: Dict[str, Any]) -> List[ValidationError]:
        """Validate basic data structure"""
        errors = []

        if not isinstance(data, dict):
            errors.append(
                ValidationError(
                    field="root",
                    message="Data must be a dictionary",
                    severity="error",
                    value=type(data).__name__,
                )
            )
            return errors

        # Check required top-level fields
        for field in self.required_fields:
            if field not in data:
                errors.append(
                    ValidationError(
                        field=field,
                        message=f"Required field '{field}' is missing",
                        severity="error",
                        suggestion=f"Add '{field}' field to the data",
                    )
                )
            elif data[field] is None:
                errors.append(
                    ValidationError(
                        field=field,
                        message=f"Field '{field}' cannot be null",
                        severity="error",
                        value=None,
                    )
                )

        return errors

    def _validate_document_number(
        self, doc_number: str
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate document number format"""
        errors = []
        warnings = []

        if not doc_number or not isinstance(doc_number, str):
            errors.append(
                ValidationError(
                    field="document_number",
                    message="Document number must be a non-empty string",
                    severity="error",
                    value=doc_number,
                )
            )
            return errors, warnings

        doc_number = doc_number.strip()

        if len(doc_number) < 3:
            warnings.append(
                ValidationError(
                    field="document_number",
                    message="Document number seems too short",
                    severity="warning",
                    value=doc_number,
                    suggestion="Verify document number is complete",
                )
            )

        if len(doc_number) > 50:
            warnings.append(
                ValidationError(
                    field="document_number",
                    message="Document number seems unusually long",
                    severity="warning",
                    value=doc_number,
                )
            )

        # Check for common patterns
        if not re.search(r"[0-9]", doc_number):
            warnings.append(
                ValidationError(
                    field="document_number",
                    message="Document number doesn't contain any numbers",
                    severity="warning",
                    value=doc_number,
                )
            )

        return errors, warnings

    def _validate_dates(
        self, data: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate date fields"""
        errors = []
        warnings = []

        doc_date = data.get("document_date")
        due_date = data.get("due_date")

        # Validate document date
        if doc_date:
            try:
                parsed_doc_date = datetime.fromisoformat(
                    doc_date.replace("/", "-").replace(".", "-")
                )

                # Check if date is reasonable
                current_date = datetime.now()
                if parsed_doc_date > current_date + timedelta(days=1):
                    warnings.append(
                        ValidationError(
                            field="document_date",
                            message="Document date is in the future",
                            severity="warning",
                            value=doc_date,
                        )
                    )

                if parsed_doc_date < current_date - timedelta(days=365 * 10):
                    warnings.append(
                        ValidationError(
                            field="document_date",
                            message="Document date is more than 10 years old",
                            severity="warning",
                            value=doc_date,
                        )
                    )

            except ValueError:
                errors.append(
                    ValidationError(
                        field="document_date",
                        message="Invalid date format",
                        severity="error",
                        value=doc_date,
                        suggestion="Use ISO format: YYYY-MM-DD",
                    )
                )

        # Validate due date
        if due_date:
            try:
                parsed_due_date = datetime.fromisoformat(
                    due_date.replace("/", "-").replace(".", "-")
                )

                if doc_date:
                    try:
                        parsed_doc_date = datetime.fromisoformat(
                            doc_date.replace("/", "-").replace(".", "-")
                        )

                        if parsed_due_date < parsed_doc_date:
                            errors.append(
                                ValidationError(
                                    field="due_date",
                                    message="Due date cannot be before document date",
                                    severity="error",
                                    value=f"doc: {doc_date}, due: {due_date}",
                                )
                            )

                        days_diff = (parsed_due_date - parsed_doc_date).days
                        if days_diff > 365:
                            warnings.append(
                                ValidationError(
                                    field="due_date",
                                    message="Due date is more than a year after document date",
                                    severity="warning",
                                    value=f"{days_diff} days",
                                )
                            )

                    except ValueError:
                        pass  # Document date validation will catch this

            except ValueError:
                errors.append(
                    ValidationError(
                        field="due_date",
                        message="Invalid due date format",
                        severity="error",
                        value=due_date,
                        suggestion="Use ISO format: YYYY-MM-DD",
                    )
                )

        return errors, warnings

    def _validate_party(
        self, party_data: Dict[str, Any], party_type: str
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate seller/buyer data"""
        errors = []
        warnings = []

        if not isinstance(party_data, dict):
            errors.append(
                ValidationError(
                    field=party_type,
                    message=f"{party_type.capitalize()} must be a dictionary",
                    severity="error",
                    value=type(party_data).__name__,
                )
            )
            return errors, warnings

        # Check required fields
        required_fields = (
            self.required_seller_fields
            if party_type == "seller"
            else self.required_buyer_fields
        )

        for field in required_fields:
            if field not in party_data or not party_data[field]:
                errors.append(
                    ValidationError(
                        field=f"{party_type}.{field}",
                        message=f"{party_type.capitalize()} {field} is required",
                        severity="error",
                    )
                )

        # Validate name
        name = party_data.get("name", "")
        if name and len(name.strip()) < 2:
            warnings.append(
                ValidationError(
                    field=f"{party_type}.name",
                    message=f"{party_type.capitalize()} name seems too short",
                    severity="warning",
                    value=name,
                )
            )

        # Validate tax ID
        tax_id = party_data.get("tax_id", "")
        if tax_id:
            tax_errors, tax_warnings = self._validate_tax_id(tax_id, party_type)
            errors.extend(tax_errors)
            warnings.extend(tax_warnings)
        else:
            warnings.append(
                ValidationError(
                    field=f"{party_type}.tax_id",
                    message=f"{party_type.capitalize()} tax ID is missing",
                    severity="warning",
                    suggestion="Tax ID is usually required for business transactions",
                )
            )

        # Validate email
        email = party_data.get("email", "")
        if email and not self._is_valid_email(email):
            warnings.append(
                ValidationError(
                    field=f"{party_type}.email",
                    message="Invalid email format",
                    severity="warning",
                    value=email,
                )
            )

        return errors, warnings

    def _validate_tax_id(
        self, tax_id: str, party_type: str
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate tax ID format"""
        errors = []
        warnings = []

        # Remove spaces and dashes
        clean_tax_id = re.sub(r"[\s\-]", "", tax_id)

        # Basic length check
        if len(clean_tax_id) < 8:
            warnings.append(
                ValidationError(
                    field=f"{party_type}.tax_id",
                    message="Tax ID seems too short",
                    severity="warning",
                    value=tax_id,
                )
            )

        if len(clean_tax_id) > 15:
            warnings.append(
                ValidationError(
                    field=f"{party_type}.tax_id",
                    message="Tax ID seems too long",
                    severity="warning",
                    value=tax_id,
                )
            )

        # Check if contains only digits (after cleaning)
        if not clean_tax_id.isdigit():
            warnings.append(
                ValidationError(
                    field=f"{party_type}.tax_id",
                    message="Tax ID contains non-numeric characters",
                    severity="warning",
                    value=tax_id,
                )
            )

        return errors, warnings

    def _validate_items(
        self, items: List[Dict[str, Any]]
    ) -> Tuple[List[ValidationError], List[ValidationError], List[str]]:
        """Validate invoice line items"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(items, list):
            errors.append(
                ValidationError(
                    field="items",
                    message="Items must be a list",
                    severity="error",
                    value=type(items).__name__,
                )
            )
            return errors, warnings, suggestions

        if len(items) == 0:
            errors.append(
                ValidationError(
                    field="items",
                    message="Invoice must contain at least one item",
                    severity="error",
                )
            )
            return errors, warnings, suggestions

        if len(items) > 1000:
            warnings.append(
                ValidationError(
                    field="items",
                    message="Unusually large number of items",
                    severity="warning",
                    value=len(items),
                )
            )

        # Validate each item
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(
                    ValidationError(
                        field=f"items[{i}]",
                        message="Item must be a dictionary",
                        severity="error",
                        value=type(item).__name__,
                    )
                )
                continue

            # Check required fields
            for field in self.required_item_fields:
                if field not in item:
                    errors.append(
                        ValidationError(
                            field=f"items[{i}].{field}",
                            message=f"Item {field} is required",
                            severity="error",
                        )
                    )

            # Validate specific fields
            description = item.get("description", "")
            if description and len(description.strip()) < 3:
                warnings.append(
                    ValidationError(
                        field=f"items[{i}].description",
                        message="Item description seems too short",
                        severity="warning",
                        value=description,
                    )
                )

            # Validate numeric fields
            quantity = item.get("quantity", 0)
            unit_price = item.get("unit_price", 0)
            total_price = item.get("total_price", 0)

            try:
                quantity = float(quantity)
                if quantity <= 0:
                    errors.append(
                        ValidationError(
                            field=f"items[{i}].quantity",
                            message="Quantity must be positive",
                            severity="error",
                            value=quantity,
                        )
                    )
                elif quantity > 1000000:
                    warnings.append(
                        ValidationError(
                            field=f"items[{i}].quantity",
                            message="Unusually large quantity",
                            severity="warning",
                            value=quantity,
                        )
                    )
            except (ValueError, TypeError):
                errors.append(
                    ValidationError(
                        field=f"items[{i}].quantity",
                        message="Quantity must be a number",
                        severity="error",
                        value=quantity,
                    )
                )

            try:
                unit_price = float(unit_price)
                if unit_price < 0:
                    warnings.append(
                        ValidationError(
                            field=f"items[{i}].unit_price",
                            message="Negative unit price",
                            severity="warning",
                            value=unit_price,
                        )
                    )
            except (ValueError, TypeError):
                errors.append(
                    ValidationError(
                        field=f"items[{i}].unit_price",
                        message="Unit price must be a number",
                        severity="error",
                        value=unit_price,
                    )
                )

            try:
                total_price = float(total_price)
                if total_price < 0:
                    warnings.append(
                        ValidationError(
                            field=f"items[{i}].total_price",
                            message="Negative total price",
                            severity="warning",
                            value=total_price,
                        )
                    )

                # Check calculation
                if quantity > 0 and unit_price >= 0:
                    expected_total = quantity * unit_price
                    if abs(total_price - expected_total) > 0.01:
                        warnings.append(
                            ValidationError(
                                field=f"items[{i}].total_price",
                                message="Total price doesn't match quantity × unit price",
                                severity="warning",
                                value=f"expected: {expected_total:.2f}, got: {total_price:.2f}",
                            )
                        )

            except (ValueError, TypeError):
                errors.append(
                    ValidationError(
                        field=f"items[{i}].total_price",
                        message="Total price must be a number",
                        severity="error",
                        value=total_price,
                    )
                )

        return errors, warnings, suggestions

    def _validate_totals(
        self, totals: Dict[str, Any], items: List[Dict[str, Any]]
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate totals against items"""
        errors = []
        warnings = []

        if not isinstance(totals, dict):
            errors.append(
                ValidationError(
                    field="totals",
                    message="Totals must be a dictionary",
                    severity="error",
                    value=type(totals).__name__,
                )
            )
            return errors, warnings

        # Check required fields
        for field in self.required_totals_fields:
            if field not in totals:
                errors.append(
                    ValidationError(
                        field=f"totals.{field}",
                        message=f"Totals {field} is required",
                        severity="error",
                    )
                )

        # Validate numeric values
        total = totals.get("total", 0)
        subtotal = totals.get("subtotal", 0)
        tax_amount = totals.get("tax_amount", 0)
        tax_rate = totals.get("tax_rate", 0)

        try:
            total = float(total)
            if total < 0:
                warnings.append(
                    ValidationError(
                        field="totals.total",
                        message="Negative total amount",
                        severity="warning",
                        value=total,
                    )
                )
            elif total == 0:
                warnings.append(
                    ValidationError(
                        field="totals.total",
                        message="Zero total amount",
                        severity="warning",
                        value=total,
                    )
                )
        except (ValueError, TypeError):
            errors.append(
                ValidationError(
                    field="totals.total",
                    message="Total must be a number",
                    severity="error",
                    value=total,
                )
            )

        # Validate against items
        if items:
            items_total = sum(
                float(item.get("total_price", 0))
                for item in items
                if isinstance(item, dict)
            )

            if subtotal:
                try:
                    subtotal = float(subtotal)
                    if abs(subtotal - items_total) > 0.01:
                        warnings.append(
                            ValidationError(
                                field="totals.subtotal",
                                message="Subtotal doesn't match sum of items",
                                severity="warning",
                                value=f"expected: {items_total:.2f}, got: {subtotal:.2f}",
                            )
                        )
                except (ValueError, TypeError):
                    pass

            # Validate tax calculation
            if subtotal and tax_rate and tax_amount:
                try:
                    expected_tax = float(subtotal) * (float(tax_rate) / 100)
                    if abs(float(tax_amount) - expected_tax) > 0.01:
                        warnings.append(
                            ValidationError(
                                field="totals.tax_amount",
                                message="Tax amount doesn't match calculation",
                                severity="warning",
                                value=f"expected: {expected_tax:.2f}, got: {tax_amount}",
                            )
                        )
                except (ValueError, TypeError):
                    pass

        return errors, warnings

    def _validate_cross_fields(
        self, data: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate relationships between fields"""
        errors = []
        warnings = []

        # Check if seller and buyer are different
        seller_name = data.get("seller", {}).get("name", "")
        buyer_name = data.get("buyer", {}).get("name", "")

        if seller_name and buyer_name and seller_name.lower() == buyer_name.lower():
            warnings.append(
                ValidationError(
                    field="seller/buyer",
                    message="Seller and buyer have the same name",
                    severity="warning",
                    suggestion="Verify this is correct",
                )
            )

        # Check tax IDs
        seller_tax_id = data.get("seller", {}).get("tax_id", "")
        buyer_tax_id = data.get("buyer", {}).get("tax_id", "")

        if seller_tax_id and buyer_tax_id and seller_tax_id == buyer_tax_id:
            warnings.append(
                ValidationError(
                    field="seller/buyer",
                    message="Seller and buyer have the same tax ID",
                    severity="warning",
                )
            )

        return errors, warnings

    def _calculate_quality_score(
        self,
        data: Dict[str, Any],
        errors: List[ValidationError],
        warnings: List[ValidationError],
    ) -> float:
        """Calculate data quality score (0.0 to 1.0)"""
        base_score = 1.0

        # Deduct for errors (more severe)
        error_penalty = len(errors) * 0.2
        warning_penalty = len(warnings) * 0.05

        # Bonus for completeness
        completeness_bonus = 0.0
        total_fields = 20  # Expected number of fields
        filled_fields = 0

        # Count filled fields
        if data.get("document_number"):
            filled_fields += 1
        if data.get("document_date"):
            filled_fields += 1
        if data.get("due_date"):
            filled_fields += 1

        seller = data.get("seller", {})
        for field in ["name", "address", "tax_id", "phone", "email"]:
            if seller.get(field):
                filled_fields += 1

        buyer = data.get("buyer", {})
        for field in ["name", "address", "tax_id", "phone", "email"]:
            if buyer.get(field):
                filled_fields += 1

        if data.get("items"):
            filled_fields += min(len(data["items"]), 5)  # Max 5 points for items

        totals = data.get("totals", {})
        for field in ["subtotal", "tax_amount", "total", "tax_rate"]:
            if totals.get(field):
                filled_fields += 1

        completeness_bonus = (filled_fields / total_fields) * 0.3

        # Calculate final score
        final_score = base_score - error_penalty - warning_penalty + completeness_bonus
        return max(0.0, min(1.0, final_score))

    def _generate_suggestions(
        self,
        data: Dict[str, Any],
        errors: List[ValidationError],
        warnings: List[ValidationError],
    ) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []

        # Add suggestions from errors and warnings
        for error in errors + warnings:
            if error.suggestion:
                suggestions.append(error.suggestion)

        # General suggestions based on data analysis
        if not data.get("due_date") and data.get("document_date"):
            suggestions.append("Consider adding a due date for payment")

        if not data.get("payment_method"):
            suggestions.append("Specify payment method for clarity")

        if not data.get("bank_account") and data.get("payment_method", "").lower() in [
            "transfer",
            "bank",
            "przelew",
        ]:
            suggestions.append("Add bank account number for bank transfers")

        items = data.get("items", [])
        if items and any(not item.get("description", "").strip() for item in items):
            suggestions.append("Provide detailed descriptions for all items")

        # Remove duplicates
        return list(set(suggestions))

    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return re.match(pattern, email) is not None

    def validate_quick(self, data: Dict[str, Any]) -> bool:
        """Quick validation - returns True if basic structure is valid"""
        if not isinstance(data, dict):
            return False

        # Check essential fields
        essential_fields = ["document_number", "items", "totals"]
        for field in essential_fields:
            if field not in data or not data[field]:
                return False

        # Check items structure
        items = data["items"]
        if not isinstance(items, list) or len(items) == 0:
            return False

        # Check totals structure
        totals = data["totals"]
        if not isinstance(totals, dict) or not totals.get("total"):
            return False

        return True

    def get_validation_summary(self, result: ValidationResult) -> str:
        """Get human-readable validation summary"""
        summary = []

        if result.is_valid:
            summary.append("✅ Data is valid")
        else:
            summary.append(f"❌ Found {len(result.errors)} errors")

        summary.append(f"📊 Quality score: {result.quality_score:.1%}")

        if result.warnings:
            summary.append(f"⚠️  {len(result.warnings)} warnings")

        if result.suggestions:
            summary.append(f"💡 {len(result.suggestions)} suggestions for improvement")

        return " | ".join(summary)


def create_validator() -> InvoiceValidator:
    """Factory function to create validator instance"""
    return InvoiceValidator()


# Validation utility functions
def validate_invoice_data(data: Dict[str, Any]) -> ValidationResult:
    """Convenience function to validate invoice data"""
    validator = create_validator()
    return validator.validate(data)


def is_valid_invoice(data: Dict[str, Any]) -> bool:
    """Quick check if invoice data is valid"""
    validator = create_validator()
    return validator.validate_quick(data)


if __name__ == "__main__":
    # Test validation
    test_data = {
        "document_number": "FV/2025/001",
        "document_date": "2025-06-15",
        "due_date": "2025-07-15",
        "seller": {"name": "Test Company", "tax_id": "123-456-78-90"},
        "buyer": {"name": "Client Company", "tax_id": "987-654-32-10"},
        "items": [
            {
                "description": "Test Service",
                "quantity": 1,
                "unit_price": 100.0,
                "total_price": 100.0,
            }
        ],
        "totals": {
            "subtotal": 100.0,
            "tax_amount": 23.0,
            "total": 123.0,
            "tax_rate": 23.0,
        },
    }

    validator = create_validator()
    result = validator.validate(test_data)

    print("Validation Result:")
    print(f"Valid: {result.is_valid}")
    print(f"Quality Score: {result.quality_score:.1%}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error.field}: {error.message}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning.field}: {warning.message}")

    if result.suggestions:
        print("\nSuggestions:")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")

    print(f"\nSummary: {validator.get_validation_summary(result)}")
    print("✅ Validator test completed")
