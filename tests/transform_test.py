import simple_pygame, pygame, unittest

class TestTransform(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.successfully_imported = simple_pygame.init([simple_pygame.TransformModule])

    @classmethod
    def tearDownClass(self) -> None:
        if self.is_imported(self):
            simple_pygame.quit([simple_pygame.TransformModule])

    def is_imported(self) -> bool:
        return simple_pygame.TransformModule in self.successfully_imported

    def test_init(self) -> None:
        if not self.is_imported():
            self.skipTest("Import simple_pygame.transform failed.")

        simple_pygame.quit([simple_pygame.TransformModule])
        self.assertIn(simple_pygame.TransformModule, simple_pygame.init([simple_pygame.TransformModule]), "Import simple_pygame.transform failed.")

    def test_fill(self) -> None:
        if not self.is_imported():
            self.skipTest("Import simple_pygame.transform failed.")

        surface = pygame.Surface((500, 500), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 255))

        rect = simple_pygame.transform.fill(surface, (255, 255, 255, 255))
        self.assertEqual(rect, pygame.Rect(0, 0, surface.get_width(), surface.get_height()), "Invalid rect.")
        self.assertEqual(pygame.transform.average_color(surface), pygame.Color(255, 255, 255, 255), "Invalid color.")

        rect = simple_pygame.transform.fill(surface, pygame.Color(25, 150, 75, 255), [-50, 50, 150, 750], pygame.BLEND_RGBA_SUB)
        self.assertEqual(rect, pygame.Rect(0, 50, 100, 450), "Invalid rect.")
        self.assertEqual(pygame.transform.average_color(surface, rect), pygame.Color(230, 105, 180, 0), "Invalid special flag.")

    def test_reverse_fill(self) -> None:
        if not self.is_imported():
            self.skipTest("Import simple_pygame.transform failed.")

        surface = pygame.Surface((500, 500), pygame.SRCALPHA)
        surface.fill((255, 255, 255, 255))

        rect = simple_pygame.transform.reverse_fill(surface, [25, 150, 75, 255], pygame.Rect(400, 525, 150, 25))
        self.assertEqual(rect, pygame.Rect(0, 0, 500, 500), "Invalid rect.")
        self.assertEqual(pygame.transform.average_color(surface, pygame.Rect(0, 0, 100, 100)), pygame.Color(25, 150, 75, 255), "Invalid color.")

        rect = simple_pygame.transform.reverse_fill(surface, pygame.Color(150, 255, 5, 10), (-50, 0, 575, 25), pygame.BLEND_RGBA_ADD)
        self.assertEqual(rect, pygame.Rect(0, 25, 500, 475), "Invalid rect.")
        self.assertEqual(pygame.transform.average_color(surface, pygame.Rect(0, 0, 500, 25)), pygame.Color(25, 150, 75, 255), "Invalid color.")
        self.assertEqual(pygame.transform.average_color(surface, rect), pygame.Color(175, 255, 80, 255), "Invalid special flag.")

if __name__ == "__main__":
    unittest.main()
