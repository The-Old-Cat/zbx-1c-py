"""
Тесты для модуля utils проекта zbx-1c-py.
"""

import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zbx_1c_py.utils.helpers import universal_filter, parse_rac_output, decode_output


class TestUtilsModule:
    """Тесты для функций модуля utils."""

    def test_universal_filter_with_list_fields(self):
        """Тест универсального фильтра с указанием полей в виде списка."""
        data = [
            {"name": "Иван", "age": 30, "city": "Москва"},
            {"name": "Мария", "age": 25, "city": "СПб"},
            {"name": "Петр", "age": 35, "city": "Новосибирск"},
        ]

        fields = ["name", "age"]
        result = universal_filter(data, fields)

        assert isinstance(result, list)
        assert len(result) == 3
        for item in result:
            assert "name" in item
            assert "age" in item
            assert "city" not in item  # Города не должно быть

    def test_universal_filter_with_dict_fields(self):
        """Тест универсального фильтра с переименованием полей."""
        data = [{"old_name": "Иван", "old_age": 30}, {"old_name": "Мария", "old_age": 25}]

        fields = {"old_name": "new_name", "old_age": "new_age"}
        result = universal_filter(data, fields)

        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert "new_name" in item
            assert "new_age" in item
            assert "old_name" not in item
            assert "old_age" not in item

    def test_universal_filter_with_missing_fields(self):
        """Тест универсального фильтра с отсутствующими полями."""
        data = [{"name": "Иван", "age": 30}, {"name": "Мария"}]  # Нет поля age

        fields = ["name", "age"]
        result = universal_filter(data, fields)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Иван"
        assert result[0]["age"] == 30
        assert result[1]["name"] == "Мария"
        assert result[1]["age"] == "N/A"  # Отсутствующее поле заменяется на N/A

    def test_universal_filter_empty_data(self):
        """Тест универсального фильтра с пустыми данными."""
        data = []
        fields = ["name", "age"]
        result = universal_filter(data, fields)

        assert not result

    def test_universal_filter_empty_fields(self):
        """Тест универсального фильтра с пустыми полями."""
        data = [{"name": "Иван", "age": 30}]

        # Список пустых полей
        result = universal_filter(data, [])
        assert result == [{}]  # Пустые словари

        # Словарь пустых полей
        result = universal_filter(data, {})
        assert result == [{}]  # Пустые словари

    def test_parse_rac_output_simple_case(self):
        """Тест парсинга простого вывода rac."""
        raw_text = '''cluster             : "a1b2c3d4-5678-90ab-cdef-1234567890ab"
name                : "Основной кластер"
port                : "1541"'''

        result = parse_rac_output(raw_text)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["cluster"] == "a1b2c3d4-5678-90ab-cdef-1234567890ab"
        assert result[0]["name"] == "Основной кластер"
        assert result[0]["port"] == "1541"

    def test_parse_rac_output_multiple_entities(self):
        """Тест парсинга вывода с несколькими сущностями."""
        raw_text = '''cluster             : "a1b2c3d4-5678-90ab-cdef-1234567890ab"
name                : "Основной кластер"
port                : "1541"

cluster             : "b2c3d4e5-6789-01ab-cdef-2345678901bc"
name                : "Резервный кластер"
port                : "1542"'''

        result = parse_rac_output(raw_text)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["cluster"] == "a1b2c3d4-5678-90ab-cdef-1234567890ab"
        assert result[1]["cluster"] == "b2c3d4e5-6789-01ab-cdef-2345678901bc"

    def test_parse_rac_output_with_empty_lines(self):
        """Тест парсинга вывода с пустыми строками."""
        raw_text = """

cluster             : "a1b2c3d4-5678-90ab-cdef-1234567890ab"
name                : "Основной кластер"

port                : "1541"


"""

        result = parse_rac_output(raw_text)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["cluster"] == "a1b2c3d4-5678-90ab-cdef-1234567890ab"
        assert result[0]["name"] == "Основной кластер"
        assert result[0]["port"] == "1541"

    def test_parse_rac_output_empty_input(self):
        """Тест парсинга пустого ввода."""
        result = parse_rac_output("")

        assert not result

    def test_parse_rac_output_no_colon(self):
        """Тест парсинга строки без двоеточия."""
        raw_text = "some random text without colon"

        result = parse_rac_output(raw_text)

        assert not result  # Нет пар "ключ: значение", значит пустой результат

    def test_parse_rac_output_no_quotes(self):
        """Тест парсинга значений без кавычек."""
        raw_text = """cluster: a1b2c3d4-5678-90ab-cdef-1234567890ab
name: Основной кластер"""

        result = parse_rac_output(raw_text)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["cluster"] == "a1b2c3d4-5678-90ab-cdef-1234567890ab"
        assert result[0]["name"] == "Основной кластер"

    def test_decode_output_with_cp866(self):
        """Тест декодирования данных в кодировке CP866."""
        # Тестируем с байтами, которые могут быть в CP866
        test_text = "тест"
        encoded_bytes = test_text.encode("cp866", errors="ignore") or test_text.encode("utf-8")

        result = decode_output(encoded_bytes)

        assert isinstance(result, str)
        # Результат может быть пустым, если не удалось декодировать как CP866
        # и не удалось как UTF-8

    def test_decode_output_with_utf8(self):
        """Тест декодирования данных в кодировке UTF-8."""
        test_text = "тест"
        encoded_bytes = test_text.encode("utf-8")

        result = decode_output(encoded_bytes)

        assert isinstance(result, str)
        assert result == test_text

    def test_decode_output_empty_bytes(self):
        """Тест декодирования пустых байтов."""
        result = decode_output(b"")

        assert result == ""

    def test_decode_output_invalid_bytes(self):
        """Тест декодирования некорректных байтов."""
        # Создаем байты, которые нельзя декодировать как CP866 или UTF-8
        invalid_bytes = b"\xff\xfe\xfd"

        result = decode_output(invalid_bytes)

        assert isinstance(result, str)
        # Результат должен быть строкой, даже если декодирование не удалось

    def test_decode_output_with_quotes(self):
        """Тест декодирования данных с кавычками."""
        test_text = '"тестовая строка"'
        encoded_bytes = test_text.encode("utf-8")

        result = decode_output(encoded_bytes)

        assert isinstance(result, str)
        assert '"' not in result  # Кавычки должны быть удалены

    def test_decode_output_strip_whitespace(self):
        """Тест декодирования с удалением пробелов."""
        test_text = "  тестовая строка  "
        encoded_bytes = test_text.encode("utf-8")

        result = decode_output(encoded_bytes)

        assert isinstance(result, str)
        assert not result.startswith(" ")
        assert not result.endswith(" ")


class TestUtilsEdgeCases:
    """Тесты для граничных условий в модуле utils."""

    def test_universal_filter_complex_nested_data(self):
        """Тест универсального фильтра с комплексными вложенными данными."""
        data = [
            {"name": "Иван", "details": {"age": 30, "city": "Москва"}},
            {"name": "Мария", "details": {"age": 25}},
        ]

        fields = ["name", "details"]
        result = universal_filter(data, fields)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Иван"
        assert result[0]["details"] == {"age": 30, "city": "Москва"}
        assert result[1]["name"] == "Мария"
        assert result[1]["details"] == {"age": 25}

    def test_universal_filter_mixed_field_types(self):
        """Тест универсального фильтра с разными типами данных."""
        data = [
            {"name": "Иван", "age": 30, "active": True, "score": 95.5},
            {"name": "Мария", "age": 25, "active": False, "score": 87.2},
        ]

        fields = ["name", "active", "score"]
        result = universal_filter(data, fields)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Иван"
        assert result[0]["active"] is True
        assert result[0]["score"] == 95.5
        assert result[1]["name"] == "Мария"
        assert result[1]["active"] is False
        assert result[1]["score"] == 87.2

    def test_parse_rac_output_multiline_values(self):
        """Тест парсинга значений, содержащих двоеточия."""
        raw_text = '''description: "Описание: с двоеточием"
name: "Тестовый кластер"'''

        result = parse_rac_output(raw_text)

        assert isinstance(result, list)
        assert len(result) == 1
        # Проверяем, что двоеточие внутри значения не мешает парсингу
        assert "name" in result[0]
        assert result[0]["name"] == "Тестовый кластер"

    def test_decode_output_special_characters(self):
        """Тест декодирования специальных символов."""
        test_text = "тест с спецсимволами: !@#$%^&*()"
        encoded_bytes = test_text.encode("utf-8")

        result = decode_output(encoded_bytes)

        assert isinstance(result, str)
        # Должны сохраниться специальные символы
