"""Check alias translation against the maintained native schematic."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from regression.common.project import ROOT, read_json
from .cells import assert_spec, capture
from .libraries import canonical_circuit, installed_library
from .replay import view_code


class LibraryMappingTest(unittest.TestCase):
    def setUp(self):
        self.folder = ROOT/'library/blocks/clock/SAR_PHASE'
        self.native = read_json(self.folder/'schematic/native.json')
        self.drawing = read_json(self.folder/'schematic/drawing.json')
        self.mapping = {'standard_cells': 'site_standard_library'}

    def test_replay_resolves_masters_and_readback_round_trips(self):
        saved = self.native['circuit']
        native = deepcopy(saved)
        for instance in native['instances']:
            instance['master'][0] = installed_library(instance['master'][0], self.mapping)
        self.assertEqual(canonical_circuit(native, self.mapping), saved)
        self.assertTrue(any(i['master'][0] == 'site_standard_library' for i in native['instances']))
        code = view_code('Replay', self.native['source_library'], saved, self.drawing,
                         library_map=self.mapping)
        self.assertIn('dbOpenCellViewByType("site_standard_library"', code)
        self.assertNotIn('"standard_cells"', code)

    def test_missing_mapping_prevents_unresolved_replay(self):
        with self.assertRaises(KeyError):
            view_code('Replay', self.native['source_library'], self.native['circuit'], self.drawing)

    def test_spec_uses_installed_library(self):
        spec = read_json(self.folder/'schematic/circuit.json')
        rows = []
        for expected in spec['instances']:
            lib, cell, view = expected['master']
            rows.append(dict(name=expected['name'], lib=installed_library(lib, self.mapping),
                             cell=cell, view=view, terms=expected['connections'],
                             params={('fingers' if k == 'nf' else k): v
                                     for k, v in expected['parameters'].items()}))
        client = Mock()
        client.schematic.read.return_value = dict(instances=rows, pins=spec['ports'])
        assert_spec(client, 'MONOTONIC_SAR', self.folder, library_map=self.mapping)
        next(row for row in rows if row['lib'] == 'site_standard_library')['lib'] = 'wrong_library'
        with self.assertRaisesRegex(ValueError, 'Master mismatch'):
            assert_spec(client, 'MONOTONIC_SAR', self.folder, library_map=self.mapping)

    def test_capture_keeps_alias_in_tracked_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'cell.json').write_bytes((self.folder/'cell.json').read_bytes())
            circuit = deepcopy(self.native['circuit'])
            for instance in circuit['instances']:
                instance['master'][0] = installed_library(instance['master'][0], self.mapping)
            client = Mock()
            def download(remote, local):
                local.write_text('')
                return Mock(ok=True)
            client.download_file.side_effect = download
            with patch('virtuoso.oa.cells.load_reader'), patch('virtuoso.oa.cells.execute'), \
                    patch('virtuoso.oa.cells.read_view', return_value=(circuit, self.drawing)):
                capture(client, 'MONOTONIC_SAR', folder, folder, '/scratch', library_map=self.mapping)
            saved = read_json(folder/'schematic/native.json')['circuit']
            self.assertEqual(saved, self.native['circuit'])


if __name__ == '__main__':
    unittest.main()
