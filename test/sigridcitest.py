# Copyright Software Improvement Group
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import tempfile
import types
import unittest
import urllib
import zipfile
from sigridci.sigridci import SystemUploadPacker, SigridApiClient, Report, TextReport


class SigridCiTest(unittest.TestCase):

    def setUp(self):
        os.environ["SIGRID_CI_ACCOUNT"] = "dummy"
        os.environ["SIGRID_CI_TOKEN"] = "dummy"

    def testCreateZipFromDirectory(self):
        sourceDir = tempfile.mkdtemp()
        self.createTempFile(sourceDir, "a.py", "a")
        self.createTempFile(sourceDir, "b.py", "b")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker()
        uploadPacker.prepareUpload(sourceDir, outputFile)

        entries = zipfile.ZipFile(outputFile).namelist()
        entries.sort()    

        self.assertEqual(entries, ["a.py", "b.py"])

    def testPreserveDirectoryStructureInUpload(self):
        sourceDir = tempfile.mkdtemp()
        subDirA = sourceDir + "/a"
        os.mkdir(subDirA)
        self.createTempFile(subDirA, "a.py", "a")
        subDirB = sourceDir + "/b"
        os.mkdir(subDirB)
        self.createTempFile(subDirB, "b.py", "b")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker()
        uploadPacker.prepareUpload(sourceDir, outputFile)
        
        entries = zipfile.ZipFile(outputFile).namelist()
        entries.sort()

        self.assertEqual(os.path.exists(outputFile), True)
        self.assertEqual(entries, ["a/a.py", "b/b.py"])
        
    def testDefaultExcludePatterns(self):
        sourceDir = tempfile.mkdtemp()
        self.createTempFile(sourceDir, "a.py", "a")
        subDir = sourceDir + "/node_modules"
        os.mkdir(subDir)
        self.createTempFile(subDir, "b.py", "b")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker()
        uploadPacker.prepareUpload(sourceDir, outputFile)

        self.assertEqual(os.path.exists(outputFile), True)
        self.assertEqual(zipfile.ZipFile(outputFile).namelist(), ["a.py"])
        
    def testCustomExcludePatterns(self):
        sourceDir = tempfile.mkdtemp()
        self.createTempFile(sourceDir, "a.py", "a")
        subDir = sourceDir + "/b"
        os.mkdir(subDir)
        self.createTempFile(subDir, "b.py", "b")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker(excludePatterns=["b/"])
        uploadPacker.prepareUpload(sourceDir, outputFile)

        self.assertEqual(os.path.exists(outputFile), True)
        self.assertEqual(zipfile.ZipFile(outputFile).namelist(), ["a.py"])
        
    def testIncludeGitHistory(self):
        sourceDir = tempfile.mkdtemp()
        self.createTempFile(sourceDir, "a.py", "a")
        subDir = sourceDir + "/.git"
        os.mkdir(subDir)
        self.createTempFile(subDir, "b.py", "b")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker([], True)
        uploadPacker.prepareUpload(sourceDir, outputFile)
        
        entries = zipfile.ZipFile(outputFile).namelist()
        entries.sort()

        self.assertEqual(entries, [".git/b.py", "a.py"])
        
    def testExcludeGitHistory(self):
        sourceDir = tempfile.mkdtemp()
        self.createTempFile(sourceDir, "a.py", "a")
        subDir = sourceDir + "/.git"
        os.mkdir(subDir)
        self.createTempFile(subDir, "b.py", "b")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker([], False)
        uploadPacker.prepareUpload(sourceDir, outputFile)

        self.assertEqual(os.path.exists(outputFile), True)
        self.assertEqual(zipfile.ZipFile(outputFile).namelist(), ["a.py"])
        
    def testErrorIfUploadExceedsMaximumSize(self):
        sourceDir = tempfile.mkdtemp()
        with open(sourceDir + "/a.py", "wb") as f:
            f.write(os.urandom(2000000))

        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker()
        uploadPacker.MAX_UPLOAD_SIZE_MB = 1
    
        self.assertRaises(Exception, uploadPacker.prepareUpload, sourceDir, outputFile)
        
    def testUsePathPrefixInUpload(self):
        sourceDir = tempfile.mkdtemp()
        subDirA = sourceDir + "/a"
        os.mkdir(subDirA)
        self.createTempFile(subDirA, "a.py", "a")
        subDirB = sourceDir + "/b"
        os.mkdir(subDirB)
        self.createTempFile(subDirB, "b.py", "b")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker(pathPrefix="frontend")
        uploadPacker.prepareUpload(sourceDir, outputFile)
        
        entries = zipfile.ZipFile(outputFile).namelist()
        entries.sort()

        self.assertEqual(os.path.exists(outputFile), True)
        self.assertEqual(entries, ["frontend/a/a.py", "frontend/b/b.py"])
        
    def testPathPrefixDoesNotLeadToDoubleSlash(self):
        sourceDir = tempfile.mkdtemp()
        self.createTempFile(sourceDir, "a.py", "a")
        
        outputFile = tempfile.mkstemp()[1]
        
        uploadPacker = SystemUploadPacker(pathPrefix="/backend/")
        uploadPacker.prepareUpload(sourceDir, outputFile)
        
        entries = zipfile.ZipFile(outputFile).namelist()
        entries.sort()

        self.assertEqual(os.path.exists(outputFile), True)
        self.assertEqual(entries, ["backend/a.py"])
        
    def testForceLowerCaseForCustomerAndSystemName(self):
        args = types.SimpleNamespace(partner="sig", customer="Aap", system="NOOT", sigridurl="")
        apiClient = SigridApiClient(args)
        
        self.assertEqual(apiClient.urlCustomerName, "aap")
        self.assertEqual(apiClient.urlSystemName, "noot")
        
    def testFeedbackTemplateOnlyContainsAsciiCharacters(self):
        with open("sigridci/sigridci-feedback-template.html", mode="r", encoding="ascii") as templateRef:
            template = templateRef.read()
            
    def testDoNotThrowExeptionFor404(self):
        args = types.SimpleNamespace(partner="sig", customer="Aap", system="NOOT", sigridurl="")
        apiClient = SigridApiClient(args)
        apiClient.processHttpError(urllib.error.HTTPError("http://www.sig.eu", 404, "", {}, None))
            
    def testDoThrowExceptionForClientError(self):
        args = types.SimpleNamespace(partner="sig", customer="Aap", system="NOOT", sigridurl="")
        apiClient = SigridApiClient(args)
        
        self.assertRaises(Exception, apiClient.processHttpError, \
            urllib.error.HTTPError("http://www.sig.eu", 400, "", {}, None), True)
            
    def testGetRefactoringCandidatesForBothOldAndNewFormat(self):
        feedback = {
            "refactoringCandidates": [{"subject":"a/b.java::Duif.vuur()","category":"introduced","metric":"UNIT_SIZE"}],
            "refactoringCandidatesPerType": {"UNIT_SIZE":["aap"]}
        }
        
        report = Report()
        unitSize = report.getRefactoringCandidates(feedback, "UNIT_SIZE")
        unitComplexity = report.getRefactoringCandidates(feedback, "UNIT_COMPLEXITY")
        
        self.assertEqual(len(unitSize), 2)
        self.assertEqual(unitSize[0]["subject"], "a/b.java::Duif.vuur()")
        self.assertEqual(unitSize[1]["subject"], "aap")
        self.assertEqual(len(unitComplexity), 0)
        
    def testFormatTextRefactoringCandidate(self):
        rc1 = {"subject" : "aap", "category" : "introduced", "metric" : "UNIT_SIZE"}
        rc2 = {"subject" : "noot\nmies", "category" : "worsened", "metric" : "DUPLICATION"}
        rc3 = {"subject" : "noot::mies", "category" : "worsened", "metric" : "UNIT_SIZE"}
        
        report = TextReport()
        
        self.assertEqual(report.formatRefactoringCandidate(rc1), \
            "    - (introduced)   aap")
        
        self.assertEqual(report.formatRefactoringCandidate(rc2), \
            "    - (worsened)     noot\n                     mies")
            
        self.assertEqual(report.formatRefactoringCandidate(rc3), \
            "    - (worsened)     noot\n                     mies")

    def createTempFile(self, dir, name, contents):
        writer = open(dir + "/" + name, "w")
        writer.write(contents)
        writer.close()
        return dir + "/" + name
    