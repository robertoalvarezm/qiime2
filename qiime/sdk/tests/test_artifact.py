# ----------------------------------------------------------------------------
# Copyright (c) 2016--, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

import collections
import os
import pkg_resources
import tempfile
import unittest
import uuid
import zipfile

from qiime.core.archiver import ArchiveMetadata
from qiime.sdk import Artifact, Provenance

from qiime.core.testing.type import IntSequence1, FourInts, Mapping
from qiime.core.testing.util import get_dummy_plugin


class TestArtifact(unittest.TestCase):
    def setUp(self):
        # Ignore the returned dummy plugin object, just run this to verify the
        # plugin exists as the tests rely on it being loaded.
        get_dummy_plugin()

        # TODO standardize temporary directories created by QIIME
        self.test_dir = tempfile.TemporaryDirectory(prefix='qiime2-test-temp-')

        self.provenance = Provenance(
            execution_uuid=uuid.UUID('7e909a23-21e2-44c2-be17-0723fae91dc8'),
            executor_reference=(
                'dummy_method_id. Details on plugin, version, website, etc. '
                'will also be included, see '
                'https://github.com/biocore/qiime2/issues/26'
            ),
            artifact_uuids={
                'input1': uuid.UUID('f16ca3d0-fe83-4b1e-8eea-7e35db3f6b0f'),
                'input2': uuid.UUID('908dece5-db23-4562-ad03-876bb5750145')
            },
            parameter_references={
                'param1': 'abc',
                'param2': '100'
            }
        )

    def tearDown(self):
        self.test_dir.cleanup()

    def test_private_constructor(self):
        with self.assertRaisesRegex(
                NotImplementedError,
                'Artifact constructor.*private.*Artifact.load'):
            Artifact()

    # Note on testing strategy below: many of the tests for `_from_view` and
    # `load` are similar, with the exception that when `load`ing, the
    # artifact's UUID is known so more specific assertions can be performed.
    # While these tests appear somewhat redundant, they are important because
    # they exercise the same operations on Artifact objects constructed from
    # different sources, whose codepaths have very different internal behavior.
    # This internal behavior could be tested explicitly but it is safer to test
    # the public API behavior (e.g. as a user would interact with the object)
    # in case the internals change.

    def test_from_view(self):
        artifact = Artifact._from_view([-1, 42, 0, 43], FourInts, None)

        self.assertEqual(artifact.type, FourInts)
        self.assertIsNone(artifact.provenance)
        # We don't know what the UUID is because it's generated within
        # Artifact._from_view.
        self.assertIsInstance(artifact.uuid, uuid.UUID)
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])
        # Can produce same view if called again.
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])

    def test_from_view_with_provenance(self):
        artifact = Artifact._from_view([-1, 42, 0, 43], FourInts,
                                       self.provenance)

        self.assertEqual(artifact.type, FourInts)
        self.assertEqual(artifact.provenance, self.provenance)
        self.assertIsInstance(artifact.uuid, uuid.UUID)
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])

    def test_from_view_different_type_with_multiple_view_types(self):
        artifact = Artifact._from_view([42, 42, 43, -999, 42], IntSequence1,
                                       None)

        self.assertEqual(artifact.type, IntSequence1)
        self.assertIsNone(artifact.provenance)
        self.assertIsInstance(artifact.uuid, uuid.UUID)

        self.assertEqual(artifact.view(list), [42, 42, 43, -999, 42])
        self.assertEqual(artifact.view(list), [42, 42, 43, -999, 42])

        self.assertEqual(artifact.view(collections.Counter),
                         collections.Counter({42: 3, 43: 1, -999: 1}))
        self.assertEqual(artifact.view(collections.Counter),
                         collections.Counter({42: 3, 43: 1, -999: 1}))

    def test_from_view_and_save(self):
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        # Using four-ints data layout because it has multiple files, some of
        # which are in a nested directory.
        artifact = Artifact._from_view([-1, 42, 0, 43], FourInts,
                                       self.provenance)

        artifact.save(fp)

        with zipfile.ZipFile(fp, mode='r') as zf:
            fps = set(zf.namelist())
            expected = {
                'artifact/VERSION',
                'artifact/metadata.yaml',
                'artifact/README.md',
                'artifact/data/file1.txt',
                'artifact/data/file2.txt',
                'artifact/data/nested/file3.txt',
                'artifact/data/nested/file4.txt'
            }
            self.assertEqual(fps, expected)

    def test_load(self):
        saved_artifact = Artifact._from_view([-1, 42, 0, 43], FourInts, None)
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        saved_artifact.save(fp)

        artifact = Artifact.load(fp)

        self.assertEqual(artifact.type, FourInts)
        self.assertIsNone(artifact.provenance)
        self.assertEqual(artifact.uuid, saved_artifact.uuid)
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])

    def test_load_with_provenance(self):
        saved_artifact = Artifact._from_view([-1, 42, 0, 43], FourInts,
                                             self.provenance)
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        saved_artifact.save(fp)

        artifact = Artifact.load(fp)

        self.assertEqual(artifact.type, FourInts)
        self.assertEqual(artifact.provenance, self.provenance)
        self.assertEqual(artifact.uuid, saved_artifact.uuid)
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])

    def test_load_different_type_with_multiple_view_types(self):
        saved_artifact = Artifact._from_view([42, 42, 43, -999, 42],
                                             IntSequence1, None)
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        saved_artifact.save(fp)

        artifact = Artifact.load(fp)

        self.assertEqual(artifact.type, IntSequence1)
        self.assertIsNone(artifact.provenance)
        self.assertEqual(artifact.uuid, saved_artifact.uuid)

        self.assertEqual(artifact.view(list), [42, 42, 43, -999, 42])
        self.assertEqual(artifact.view(list), [42, 42, 43, -999, 42])

        self.assertEqual(artifact.view(collections.Counter),
                         collections.Counter({42: 3, 43: 1, -999: 1}))
        self.assertEqual(artifact.view(collections.Counter),
                         collections.Counter({42: 3, 43: 1, -999: 1}))

    def test_load_and_save(self):
        fp1 = os.path.join(self.test_dir.name, 'artifact1.qza')
        fp2 = os.path.join(self.test_dir.name, 'artifact2.qza')
        artifact = Artifact._from_view([-1, 42, 0, 43], FourInts,
                                       self.provenance)
        artifact.save(fp1)

        artifact = Artifact.load(fp1)
        # Overwriting its source file works.
        artifact.save(fp1)
        # Saving to a new file works.
        artifact.save(fp2)

        with zipfile.ZipFile(fp1, mode='r') as zf:
            fps = set(zf.namelist())
            expected = {
                'artifact1/VERSION',
                'artifact1/metadata.yaml',
                'artifact1/README.md',
                'artifact1/data/file1.txt',
                'artifact1/data/file2.txt',
                'artifact1/data/nested/file3.txt',
                'artifact1/data/nested/file4.txt'
            }
            self.assertEqual(fps, expected)

        with zipfile.ZipFile(fp2, mode='r') as zf:
            fps = set(zf.namelist())
            expected = {
                'artifact2/VERSION',
                'artifact2/metadata.yaml',
                'artifact2/README.md',
                'artifact2/data/file1.txt',
                'artifact2/data/file2.txt',
                'artifact2/data/nested/file3.txt',
                'artifact2/data/nested/file4.txt'
            }
            self.assertEqual(fps, expected)

    def test_roundtrip(self):
        fp1 = os.path.join(self.test_dir.name, 'artifact1.qza')
        fp2 = os.path.join(self.test_dir.name, 'artifact2.qza')
        artifact = Artifact._from_view([-1, 42, 0, 43], FourInts,
                                       self.provenance)
        artifact.save(fp1)

        artifact1 = Artifact.load(fp1)
        artifact1.save(fp2)
        artifact2 = Artifact.load(fp2)

        self.assertEqual(artifact1.type, artifact2.type)
        self.assertEqual(artifact1.provenance, artifact2.provenance)
        self.assertEqual(artifact1.uuid, artifact2.uuid)
        self.assertEqual(artifact1.view(list), artifact2.view(list))
        self.assertEqual(artifact1.view(list), artifact2.view(list))

    def test_load_from_externally_created_zipfile(self):
        # If a user unzips a .qza to inspect contents and rezips using a
        # different ZIP library/implementation than the one provided by Python,
        # loading, saving, etc. should still work as expected. The Python ZIP
        # implementation doesn't store directories as entries when writing, but
        # the `zip` Unix and OS X command line utilities include both
        # directories and filepaths as entries. When reading these files with
        # Python's ZIP implementation, the directory entries are visible, so
        # their presence needs to be accounted for when extracting.
        #
        # The following artifact was created with:
        #
        #     artifact = Artifact._from_view([-1, 42, 0, 43], FourInts,
        #                                    self.provenance)
        #     artifact.save('externally_created_zipfile.qza')
        #
        # Unzip and rezip using command line utility:
        #
        #     unzip externally_created_zipfile.qza
        #     rm externally_created_zipfile.qza
        #     zip -r externally_created_zipfile.qza externally_created_zipfile
        #
        fp = pkg_resources.resource_filename(
            'qiime.sdk.tests', 'data/externally_created_zipfile.qza')

        with zipfile.ZipFile(fp, mode='r') as zf:
            fps = set(zf.namelist())
            expected = {
                # These are extra directory entries included by `zip` command
                # line utility.
                'externally_created_zipfile/',
                'externally_created_zipfile/data/',
                'externally_created_zipfile/data/nested/',

                'externally_created_zipfile/VERSION',
                'externally_created_zipfile/metadata.yaml',
                'externally_created_zipfile/README.md',
                'externally_created_zipfile/data/file1.txt',
                'externally_created_zipfile/data/file2.txt',
                'externally_created_zipfile/data/nested/file3.txt',
                'externally_created_zipfile/data/nested/file4.txt'
            }
            self.assertEqual(fps, expected)

        artifact = Artifact.load(fp)

        self.assertEqual(artifact.type, FourInts)
        self.assertEqual(artifact.provenance, self.provenance)
        self.assertIsInstance(artifact.uuid, uuid.UUID)
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])
        self.assertEqual(artifact.view(list), [-1, 42, 0, 43])

        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        artifact.save(fp)

        with zipfile.ZipFile(fp, mode='r') as zf:
            fps = set(zf.namelist())
            expected = {
                # Directory entries should not be present.
                'artifact/VERSION',
                'artifact/metadata.yaml',
                'artifact/README.md',
                'artifact/data/file1.txt',
                'artifact/data/file2.txt',
                'artifact/data/nested/file3.txt',
                'artifact/data/nested/file4.txt'
            }
            self.assertEqual(fps, expected)

    def test_load_with_archive_filepath_modified(self):
        # Save an artifact for use in the following test case.
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        Artifact._from_view([-1, 42, 0, 43], FourInts, None).save(fp)

        # Load the artifact from a filepath then save a different artifact to
        # the same filepath. Assert that both artifacts produce the correct
        # views of their data.
        #
        # `load` used to be lazy, only extracting data when it needed to (e.g.
        # when `save` or `view` was called). This was buggy as the filepath
        # could have been deleted, or worse, modified to contain a different
        # .qza file. Thus, the wrong archive could be extracted on demand, or
        # the archive could be missing altogether. There isn't an easy
        # cross-platform compatible way to solve this problem, so Artifact.load
        # is no longer lazy and always extracts its data immediately. The real
        # motivation for lazy loading was for quick inspection of archives
        # without extracting/copying data, so that API is now provided through
        # Artifact.peek.
        artifact1 = Artifact.load(fp)
        Artifact._from_view([10, 11, 12, 13], FourInts, None).save(fp)
        artifact2 = Artifact.load(fp)

        self.assertEqual(artifact1.view(list), [-1, 42, 0, 43])
        self.assertEqual(artifact2.view(list), [10, 11, 12, 13])

    def test_extract(self):
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        artifact = Artifact._from_view([-1, 42, 0, 43], FourInts,
                                       self.provenance)
        artifact.save(fp)

        output_dir = os.path.join(self.test_dir.name, 'artifact-extract-test')
        result_dir = Artifact.extract(fp, output_dir=output_dir)
        self.assertEqual(result_dir, output_dir)

        contents = [
            'artifact/VERSION',
            'artifact/metadata.yaml',
            'artifact/README.md',
            'artifact/data/file1.txt',
            'artifact/data/file2.txt',
            'artifact/data/nested/file3.txt',
            'artifact/data/nested/file4.txt']
        for fp in contents:
            expected_fp = os.path.join(output_dir, fp)
            self.assertTrue(os.path.exists(expected_fp),
                            'File %s was not extracted.' % fp)

    def test_peek(self):
        artifact = Artifact._from_view([0, 0, 42, 1000], FourInts, None)
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        artifact.save(fp)

        metadata = Artifact.peek(fp)

        self.assertIsInstance(metadata, ArchiveMetadata)
        self.assertEqual(metadata.type, FourInts)
        self.assertIsNone(metadata.provenance)
        self.assertEqual(metadata.uuid, artifact.uuid)

    def test_peek_with_provenance(self):
        artifact = Artifact._from_view({'foo': 'bar', 'baz': 'bazz'}, Mapping,
                                       self.provenance)
        fp = os.path.join(self.test_dir.name, 'artifact.qza')
        artifact.save(fp)

        metadata = Artifact.peek(fp)

        self.assertIsInstance(metadata, ArchiveMetadata)
        self.assertEqual(metadata.type, Mapping)
        self.assertEqual(metadata.provenance, self.provenance)
        self.assertEqual(metadata.uuid, artifact.uuid)


if __name__ == '__main__':
    unittest.main()
