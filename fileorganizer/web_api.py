"""
Simple web API for file organization assistant.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import logging

from .core.scanner_v2 import ScannerV2
from .duplicates import DuplicateManager
from .database import Database
from .undo import UndoManager

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='web/static', template_folder='web/templates')
CORS(app)

# Global instances
db = Database()
undo_manager = UndoManager(db)


@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory(app.template_folder, 'index.html')


@app.route('/api/scan', methods=['POST'])
def scan_directory():
    """Scan a directory."""
    data = request.json
    directory = data.get('directory')

    if not directory:
        return jsonify({'error': 'Directory parameter required'}), 400

    try:
        scanner = ScannerV2(
            directory,
            use_cache=data.get('use_cache', True),
            parallel_hashing=data.get('parallel', True),
            smart_detection=data.get('smart', False),
            show_progress=False  # No progress in API mode
        )

        results = scanner.scan(
            include_hidden=data.get('include_hidden', False),
            quick_scan=data.get('quick', False)
        )

        # Simplify results for JSON
        simplified = {
            'file_count': results['file_count'],
            'total_size': results['total_size'],
            'scan_duration': results['scan_duration'],
            'duplicate_groups': len(results['duplicates']),
            'cache_hits': results.get('cache_hits', 0),
            'by_extension': {
                ext: len(files)
                for ext, files in results['by_extension'].items()
            }
        }

        return jsonify(simplified)

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/duplicates', methods=['POST'])
def find_duplicates():
    """Find duplicate files."""
    data = request.json
    directory = data.get('directory')

    if not directory:
        return jsonify({'error': 'Directory parameter required'}), 400

    try:
        scanner = ScannerV2(directory, show_progress=False)
        results = scanner.scan()
        duplicates = results['duplicates']

        duplicate_manager = DuplicateManager()
        analysis = duplicate_manager.analyze_duplicates(duplicates)

        # Format duplicate groups for API
        duplicate_groups = []
        for hash_val, files in list(duplicates.items())[:50]:  # Limit to 50 groups
            duplicate_groups.append({
                'hash': hash_val,
                'count': len(files),
                'size': files[0]['size'],
                'wasted_space': files[0]['size'] * (len(files) - 1),
                'files': [
                    {
                        'path': f['path'],
                        'modified': f['modified']
                    }
                    for f in files
                ]
            })

        return jsonify({
            'duplicate_groups': analysis['duplicate_groups'],
            'total_duplicate_files': analysis['total_duplicate_files'],
            'wasted_space': analysis['wasted_space'],
            'groups': duplicate_groups
        })

    except Exception as e:
        logger.error(f"Duplicate detection failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get operation history."""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = db.get_operation_history(limit=limit)

        return jsonify({
            'operations': history
        })

    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/undo', methods=['GET'])
def list_undoable():
    """List undoable operations."""
    try:
        operations = undo_manager.get_undo_list()

        formatted = []
        for op in operations:
            formatted.append({
                'id': op['id'],
                'type': op['operation_type'],
                'command': op['command'],
                'timestamp': op['timestamp'],
                'file_count': op['file_count']
            })

        return jsonify({
            'undoable_operations': formatted
        })

    except Exception as e:
        logger.error(f"Failed to list undoable: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/undo/<int:operation_id>', methods=['POST'])
def undo_operation(operation_id):
    """Undo an operation."""
    try:
        data = request.json or {}
        dry_run = data.get('dry_run', False)

        results = undo_manager.undo_operation(operation_id, dry_run=dry_run)

        return jsonify({
            'operation_id': results['operation_id'],
            'operation_type': results['operation_type'],
            'undone_count': len(results['undone']),
            'failed_count': len(results['failed']),
            'dry_run': results['dry_run']
        })

    except Exception as e:
        logger.error(f"Undo failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics."""
    try:
        stats = db.get_statistics()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({'error': str(e)}), 500


def run_server(host='0.0.0.0', port=5000, debug=False):
    """
    Run the web server.

    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
