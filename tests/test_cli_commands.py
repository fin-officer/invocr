"""
Tests for CLI commands
"""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from invocr.cli.commands.batch_command import _process_single_file, batch_command
from invocr.core.converter import convert_document


def test_process_single_file():
    """Test the _process_single_file function"""
    with patch('invocr.cli.commands.batch_command.convert_document') as mock_convert:
        # Setup mock return value (success, error)
        mock_convert.return_value = (True, None)
        
        # Call the function
        success, file_path, error = _process_single_file(
            input_path="test.pdf",
            output_path="test.json",
            output_format="json",
            languages=["en"]
        )
        
        # Verify results
        assert success is True
        assert file_path == "test.pdf"
        assert error is None
        
        # Verify convert_document was called with correct parameters
        mock_convert.assert_called_once_with(
            input_file="test.pdf",
            output_file="test.json",
            output_format="json",
            languages=["en"]
        )


def test_process_single_file_error():
    """Test _process_single_file with error case"""
    with patch('invocr.cli.commands.batch_command.convert_document') as mock_convert:
        # Setup mock to raise exception
        mock_convert.side_effect = Exception("Test error")
        
        # Call the function
        success, file_path, error = _process_single_file(
            input_path="test.pdf",
            output_path="test.json",
            output_format="json",
            languages=["en"]
        )
        
        # Verify results
        assert success is False
        assert file_path == "test.pdf"
        assert error == "Test error"


def test_batch_command():
    """Test the batch_command function with mocked file processing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Create a test PDF file
        test_file = input_dir / "test.pdf"
        with open(test_file, "wb") as f:
            f.write(b"%PDF-1.7\n")  # Minimal PDF header
        
        with patch('invocr.cli.commands.batch_command._process_single_file') as mock_process:
            # Setup mock return value (success, file_path, error)
            mock_process.return_value = (True, str(test_file), None)
            
            # Call batch_command
            with patch('click.Path'):  # Mock click.Path to avoid validation
                batch_command(
                    input_dir=str(input_dir),
                    output_dir=str(output_dir),
                    output_format="json",
                    max_workers=1,
                    languages=["en"]
                )
            
            # Verify _process_single_file was called
            mock_process.assert_called_once()
            
            # Check call arguments
            args, kwargs = mock_process.call_args
            assert str(test_file) in args[0]  # input_path
            assert kwargs.get('output_format') == "json"
            assert kwargs.get('languages') == ["en"]
