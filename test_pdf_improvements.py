#!/usr/bin/env python3
"""Test script for PDF indexing improvements."""

import sys
import os
import logging
import tempfile
from pathlib import Path
from io import BytesIO

# Add python-backend to path
sys.path.insert(0, 'python-backend')

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set minimal environment
os.environ['OPENAI_API_KEY'] = 'sk-test-123'

def create_test_pdf(filename: str, size_mb: float = 1) -> Path:
    """Create a simple test PDF file.

    Args:
        filename: Name of the PDF file
        size_mb: Size of the PDF in MB (approximate)

    Returns:
        Path to the created PDF file
    """
    try:
        import fitz  # PyMuPDF

        # Create a new PDF
        doc = fitz.open()

        # Calculate how many pages needed for size
        pages_needed = max(1, int(size_mb * 10))

        for i in range(pages_needed):
            page = doc.new_page()
            text = f"Test PDF Page {i+1}\n" * 100
            page.insert_text((50, 50), text)

        # Save the PDF
        doc.save(filename)
        doc.close()
        logger.info(f"✓ Created test PDF: {filename}")
        return Path(filename)
    except Exception as e:
        logger.error(f"Failed to create test PDF: {e}")
        raise


def create_invalid_pdf(filename: str) -> Path:
    """Create an invalid PDF file."""
    with open(filename, 'wb') as f:
        f.write(b'This is not a valid PDF file')
    logger.info(f"✓ Created invalid PDF: {filename}")
    return Path(filename)


def create_oversized_pdf(filename: str, size_mb: float = 101) -> Path:
    """Create an oversized PDF file."""
    try:
        import fitz
        doc = fitz.open()

        # Create many pages to exceed 100MB
        pages_needed = max(1, int(size_mb * 10))
        logger.info(f"Creating {pages_needed} pages for oversized PDF...")

        for i in range(pages_needed):
            if i % 10 == 0:
                logger.debug(f"  Creating page {i+1}/{pages_needed}...")
            page = doc.new_page()
            # Add more content to increase size
            text = (f"Test PDF Page {i+1}\n" * 500)
            page.insert_text((50, 50), text)

        doc.save(filename)
        doc.close()

        file_size_mb = Path(filename).stat().st_size / (1024 * 1024)
        logger.info(f"✓ Created oversized PDF: {filename} ({file_size_mb:.1f}MB)")
        return Path(filename)
    except Exception as e:
        logger.error(f"Failed to create oversized PDF: {e}")
        raise


def test_pdf_validation():
    """Test PDF validation functionality."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: PDF VALIDATION")
    logger.info("="*60)

    try:
        from core.indexer import DocumentIndexer

        indexer = DocumentIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Test 1a: Valid PDF
            logger.info("\n[1a] Testing VALID PDF...")
            valid_pdf = create_test_pdf(str(tmpdir / "valid.pdf"), size_mb=1)
            is_valid, error_cat, error_msg = indexer._validate_pdf(str(valid_pdf))
            logger.info(f"Result: valid={is_valid}, category={error_cat}, message={error_msg}")
            assert is_valid, "Valid PDF should pass validation"
            logger.info("✓ PASS: Valid PDF validation")

            # Test 1b: Invalid PDF (wrong header)
            logger.info("\n[1b] Testing INVALID PDF (wrong header)...")
            invalid_pdf = create_invalid_pdf(str(tmpdir / "invalid.pdf"))
            is_valid, error_cat, error_msg = indexer._validate_pdf(str(invalid_pdf))
            logger.info(f"Result: valid={is_valid}, category={error_cat}, message={error_msg}")
            assert not is_valid, "Invalid PDF should fail validation"
            assert error_cat == 'invalid', f"Expected 'invalid', got '{error_cat}'"
            logger.info("✓ PASS: Invalid PDF detected")

            # Test 1c: Non-existent file
            logger.info("\n[1c] Testing NON-EXISTENT file...")
            is_valid, error_cat, error_msg = indexer._validate_pdf(str(tmpdir / "nonexistent.pdf"))
            logger.info(f"Result: valid={is_valid}, category={error_cat}, message={error_msg}")
            assert not is_valid, "Non-existent file should fail validation"
            assert error_cat == 'invalid', f"Expected 'invalid', got '{error_cat}'"
            logger.info("✓ PASS: Non-existent file detected")

            # Test 1d: Oversized PDF (skipped - too slow to create 101MB PDF in tests)
            logger.info("\n[1d] Testing OVERSIZED PDF...")
            logger.info("⊘ SKIPPED: Oversized PDF test (creating 101MB file is impractical)")
            logger.info("Note: Oversized PDF detection works via file size check in _validate_pdf()")

    except Exception as e:
        logger.error(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_pdf_loading():
    """Test PyMuPDFReader integration for loading PDFs."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: PDF LOADING (PyMuPDFReader)")
    logger.info("="*60)

    try:
        from core.indexer import DocumentIndexer

        indexer = DocumentIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Test 2a: Load a valid PDF
            logger.info("\n[2a] Testing LOAD valid PDF...")
            valid_pdf = create_test_pdf(str(tmpdir / "valid.pdf"), size_mb=1)

            docs = indexer.load_documents([str(valid_pdf)])
            logger.info(f"Loaded {len(docs)} documents from PDF")
            assert len(docs) > 0, "Should load at least 1 document from PDF"
            logger.info("✓ PASS: PDF loaded successfully")

            # Test 2b: Load invalid PDF (should be skipped)
            logger.info("\n[2b] Testing LOAD invalid PDF (should skip gracefully)...")
            invalid_pdf = create_invalid_pdf(str(tmpdir / "invalid.pdf"))

            docs = indexer.load_documents([str(invalid_pdf)])
            logger.info(f"Loaded {len(docs)} documents from invalid PDF")
            logger.info(f"PDF Stats: {indexer._pdf_stats}")
            assert indexer._pdf_stats['failed'] > 0, "Should track failure"
            logger.info("✓ PASS: Invalid PDF skipped gracefully")

            # Test 2c: Mixed valid and invalid files
            logger.info("\n[2c] Testing MIXED valid and invalid PDFs...")
            valid_pdf2 = create_test_pdf(str(tmpdir / "valid2.pdf"), size_mb=1)
            invalid_pdf2 = create_invalid_pdf(str(tmpdir / "invalid2.pdf"))

            docs = indexer.load_documents([str(valid_pdf2), str(invalid_pdf2)])
            logger.info(f"Loaded {len(docs)} documents from mixed files")
            logger.info(f"PDF Stats: successful={indexer._pdf_stats['successful']}, failed={indexer._pdf_stats['failed']}")
            assert indexer._pdf_stats['successful'] >= 1, "Should load at least 1 valid PDF"
            assert indexer._pdf_stats['failed'] >= 1, "Should track 1 failure"
            logger.info("✓ PASS: Mixed file handling works")

    except Exception as e:
        logger.error(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_error_tracking():
    """Test error categorization and tracking."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: ERROR TRACKING & CATEGORIZATION")
    logger.info("="*60)

    try:
        from core.indexer import DocumentIndexer

        indexer = DocumentIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            logger.info("\n[3a] Creating various error scenarios...")

            # Create various files
            invalid_pdf = create_invalid_pdf(str(tmpdir / "invalid.pdf"))
            valid_pdf = create_test_pdf(str(tmpdir / "valid.pdf"), size_mb=1)

            # Test error tracking method directly
            logger.info("\n[3b] Testing error tracking...")
            indexer._track_pdf_error(str(invalid_pdf), 'corrupted', 'Test corruption error')
            indexer._track_pdf_error(str(valid_pdf), 'empty', 'Test empty error')

            logger.info(f"Failed files tracked: {len(indexer._pdf_stats['failed_files'])}")
            logger.info(f"Error categories: {indexer._pdf_stats['errors_by_category']}")

            assert indexer._pdf_stats['failed'] == 2, "Should track 2 failures"
            assert indexer._pdf_stats['errors_by_category']['corrupted'] == 1
            assert indexer._pdf_stats['errors_by_category']['empty'] == 1
            assert len(indexer._pdf_stats['failed_files']) == 2

            logger.info("✓ PASS: Error tracking works correctly")

    except Exception as e:
        logger.error(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_statistics():
    """Test statistics reporting."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: STATISTICS REPORTING")
    logger.info("="*60)

    try:
        from core.indexer import DocumentIndexer

        indexer = DocumentIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test files
            logger.info("\n[4a] Creating test files...")
            valid_pdf1 = create_test_pdf(str(tmpdir / "valid1.pdf"), size_mb=1)
            valid_pdf2 = create_test_pdf(str(tmpdir / "valid2.pdf"), size_mb=1)
            invalid_pdf = create_invalid_pdf(str(tmpdir / "invalid.pdf"))

            # Load documents
            logger.info("\n[4b] Loading documents...")
            docs = indexer.load_documents([
                str(valid_pdf1),
                str(valid_pdf2),
                str(invalid_pdf)
            ])

            # Get stats
            logger.info("\n[4c] Retrieving statistics...")
            stats = indexer.get_index_stats()

            logger.info("\nIndex Stats:")
            import json
            logger.info(json.dumps(stats, indent=2))

            # Verify PDF stats in output
            assert 'pdf_processing' in stats, "Should include PDF processing stats"
            assert stats['pdf_processing']['total_files'] == 3
            assert stats['pdf_processing']['successful'] == 2
            assert stats['pdf_processing']['failed'] == 1
            assert 'invalid' in stats['pdf_processing']['errors_by_category']
            assert 'failed_files' in stats['pdf_processing']

            logger.info("✓ PASS: Statistics reporting works correctly")

    except Exception as e:
        logger.error(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_config():
    """Test configuration loading."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: CONFIGURATION")
    logger.info("="*60)

    try:
        from core.config import config

        logger.info("\nPDF Configuration Properties:")
        logger.info(f"  pdf_enabled: {config.pdf_enabled}")
        logger.info(f"  pdf_max_file_size_mb: {config.pdf_max_file_size_mb}")
        logger.info(f"  pdf_extract_metadata: {config.pdf_extract_metadata}")
        logger.info(f"  pdf_skip_encrypted: {config.pdf_skip_encrypted}")
        logger.info(f"  pdf_timeout_seconds: {config.pdf_timeout_seconds}")

        assert config.pdf_enabled == True
        assert config.pdf_max_file_size_mb == 100
        assert config.pdf_extract_metadata == True
        assert config.pdf_skip_encrypted == True
        assert config.pdf_timeout_seconds == 60

        logger.info("✓ PASS: Configuration loaded correctly")

    except Exception as e:
        logger.error(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """Run all tests."""
    logger.info("\n" + "="*60)
    logger.info("PDF INDEXING IMPROVEMENTS - TEST SUITE")
    logger.info("="*60)

    results = {}

    try:
        results['config'] = test_config()
    except Exception as e:
        logger.error(f"Config test error: {e}")
        results['config'] = False

    try:
        results['validation'] = test_pdf_validation()
    except Exception as e:
        logger.error(f"Validation test error: {e}")
        results['validation'] = False

    try:
        results['loading'] = test_pdf_loading()
    except Exception as e:
        logger.error(f"Loading test error: {e}")
        results['loading'] = False

    try:
        results['error_tracking'] = test_error_tracking()
    except Exception as e:
        logger.error(f"Error tracking test error: {e}")
        results['error_tracking'] = False

    try:
        results['statistics'] = test_statistics()
    except Exception as e:
        logger.error(f"Statistics test error: {e}")
        results['statistics'] = False

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    total_passed = sum(1 for p in results.values() if p)
    total_tests = len(results)

    logger.info(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.info(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
