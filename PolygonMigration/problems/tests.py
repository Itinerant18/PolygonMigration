from django.test import TestCase, override_settings

from .models import Problem, ProblemTestCase


def make_problem(polygon_id="1001"):
    return Problem.objects.create(
        polygon_id=polygon_id,
        title="Test Problem %s" % polygon_id,
        slug="test-problem-%s" % polygon_id,
        difficulty="easy",
    )


def save_all_test_cases(problem, test_cases):
    ProblemTestCase.objects.filter(problem=problem).delete()
    saved = 0
    for order, test in enumerate(test_cases, start=1):
        ProblemTestCase.objects.create(
            problem=problem,
            is_sample=test.get("is_sample", False),
            input=test.get("input", "") or "",
            output=test.get("output", "") or "",
            description=test.get("description", ""),
            order=order,
        )
        saved += 1
    return saved


class TestCaseMigrationTests(TestCase):
    def test_all_fetched_cases_saved(self):
        problem = make_problem("2001")
        fetched = [
            {"input": "in %s" % i, "output": "out %s" % i,
             "is_sample": i <= 2, "description": ""}
            for i in range(1, 22)
        ]
        saved = save_all_test_cases(problem, fetched)
        self.assertEqual(saved, 21)
        self.assertEqual(ProblemTestCase.objects.filter(problem=problem).count(), 21)
        self.assertEqual(ProblemTestCase.objects.filter(problem=problem, is_sample=True).count(), 2)

    def test_remigration_creates_no_duplicates(self):
        problem = make_problem("2002")
        fetched = [{"input": "a", "output": "b", "is_sample": False, "description": ""} for _ in range(21)]
        save_all_test_cases(problem, fetched)
        save_all_test_cases(problem, fetched)
        self.assertEqual(ProblemTestCase.objects.filter(problem=problem).count(), 21)

    def test_full_text_is_not_truncated(self):
        problem = make_problem("2003")
        long_text = "x" * 1000
        save_all_test_cases(problem, [{"input": long_text, "output": long_text}])
        tc = ProblemTestCase.objects.get(problem=problem)
        self.assertEqual(len(tc.input), 1000)
        self.assertEqual(len(tc.output), 1000)

    def test_drive_ids_can_be_saved(self):
        problem = make_problem("2004")
        tc = ProblemTestCase.objects.create(
            problem=problem, input="1", output="2", order=1,
        )
        tc.drive_input_file_id = "input-id-123"
        tc.drive_output_file_id = "output-id-456"
        tc.save()
        tc.refresh_from_db()
        self.assertEqual(tc.drive_input_file_id, "input-id-123")
        self.assertEqual(tc.drive_output_file_id, "output-id-456")

    @override_settings(GOOGLE_DRIVE_FOLDER_ID="")
    def test_upload_without_folder_gives_error(self):
        from .google_drive import upload_text_file
        with self.assertRaises(Exception):
            upload_text_file("problem_1_test_01.txt", "hello")
