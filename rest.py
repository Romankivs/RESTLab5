from flask import Flask, jsonify, request, url_for

class DynamicTable:
    def __init__(self, column_info):
        self.column_info = column_info
        self.rows = []

    def add_column(self, column_name, column_type):
        if column_name in [col[0] for col in self.column_info]:
            raise ValueError(f"Column '{column_name}' already exists")

        self.column_info.append((column_name, column_type))

        for row in self.rows:
            row[column_name] = None

    def delete_column(self, column_name):
        if column_name not in [col[0] for col in self.column_info]:
            raise ValueError(f"Column '{column_name}' does not exist")

        index = [col[0] for col in self.column_info].index(column_name)
        del self.column_info[index]

        for row in self.rows:
            del row[column_name]

    def add_row(self, values):
        if len(values) != len(self.column_info):
            raise ValueError("Number of values must match the number of columns")

        validated_values = []
        for i, (column_name, column_type) in enumerate(self.column_info):
            value = values[i]
            if not isinstance(value, column_type):
                raise ValueError(f"Invalid type for column '{column_name}'. Expected {column_type}, got {type(value)}")
            validated_values.append(value)

        row = dict(zip([col[0] for col in self.column_info], validated_values))
        self.rows.append(row)
    
    def update_row(self, row_index, values):
        if row_index < 0 or row_index >= len(self.rows):
            raise IndexError("Row index is out of bounds")

        if len(values) != len(self.column_info):
            raise ValueError("Number of values must match the number of columns")

        validated_values = []
        for i, (column_name, column_type) in enumerate(self.column_info):
            value = values[i]
            if not isinstance(value, column_type):
                raise ValueError(f"Invalid type for column '{column_name}'. Expected {column_type}, got {type(value)}")
            validated_values.append(value)

        self.rows[row_index] = dict(zip([col[0] for col in self.column_info], validated_values))

    def display_table(self):
        # Display the table header
        header = "|".join([col[0] for col in self.column_info])
        print(header)
        print("-" * len(header))

        # Display each row
        for row in self.rows:
            row_values = [str(row.get(column[0], "")) for column in self.column_info]
            print("|".join(row_values))

    def remove_duplicates(self):
        seen_rows = set()
        unique_rows = []

        for row in self.rows:
            key_values = tuple(row[column] for column, _ in self.column_info)
            if key_values not in seen_rows:
                seen_rows.add(key_values)
                unique_rows.append(row)

        self.rows = unique_rows

class Database:
    def __init__(self):
        self.tables = {}

    def add_table(self, table_name, column_info):
        if table_name in self.tables:
            raise ValueError(f"Table '{table_name}' already exists")

        self.tables[table_name] = DynamicTable(column_info)

    def remove_table(self, table_name):
        if table_name not in self.tables:
            raise ValueError(f"Table '{table_name}' does not exist")

        del self.tables[table_name]

    def display_tables(self):
        for table_name, dynamic_table in self.tables.items():
            print(f"\nTable: {table_name}")
            dynamic_table.display_table()


app = Flask(__name__)
database = Database()

def generate_table_links(table_name):
    links = {
        'self': url_for('get_table', table_name=table_name, _external=True),
        'rows': url_for('add_row', table_name=table_name, _external=True),
        'columns': url_for('add_column', table_name=table_name, _external=True),
        'remove_duplicates': url_for('remove_duplicates', table_name=table_name, _external=True),
    }

    return links

@app.route('/tables', methods=['GET'])
def get_tables():
    tables = []
    for table_name, dynamic_table in database.tables.items():
        table_data = {
            'table_name': table_name,
            'column_info': [{'column_name': col[0], 'column_type': str(col[1].__name__)} for col in dynamic_table.column_info],
            'rows': dynamic_table.rows,
            '_links': generate_table_links(table_name)
        }
        tables.append(table_data)

    return jsonify({'tables': tables})

@app.route('/tables/<table_name>', methods=['GET'])
def get_table(table_name):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    dynamic_table = database.tables[table_name]
    
    # Convert column types to string representations
    column_info = [{'column_name': col[0], 'column_type': str(col[1].__name__)} for col in dynamic_table.column_info]
    
    table_data = {
        'table_name': table_name,
        'column_info': column_info,
        'rows': dynamic_table.rows,
        '_links': generate_table_links(table_name)
    }
    
    return jsonify({'table': table_data})

@app.route('/tables', methods=['POST'])
def add_table():
    data = request.json
    table_name = data.get('table_name')
    column_info = data.get('column_info')

    if not table_name or not column_info:
        return jsonify({'error': 'Table name and column information are required'}), 400

    converted_column_info = []
    for col_name, col_type in column_info:
        try:
            converted_column_info.append((col_name, eval(col_type)))
        except (ValueError, TypeError):
            return jsonify({'error': f"Invalid column type '{col_type}' for column '{col_name}'"}), 400

    try:
        database.add_table(table_name, converted_column_info)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': f"Table '{table_name}' added successfully"}), 201

@app.route('/tables/<table_name>', methods=['DELETE'])
def remove_table(table_name):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    try:
        database.remove_table(table_name)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': f"Table '{table_name}' removed successfully"}), 200

@app.route('/tables/<table_name>/rows', methods=['POST'])
def add_row(table_name):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    dynamic_table = database.tables[table_name]
    data = request.json

    try:
        dynamic_table.add_row(data.get('values'))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': f"Row added to '{table_name}' successfully"}), 201

@app.route('/tables/<table_name>/rows/<int:row_index>', methods=['PUT'])
def update_row(table_name, row_index):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    dynamic_table = database.tables[table_name]
    data = request.json

    try:
        dynamic_table.update_row(row_index, data.get('values'))
    except (ValueError, IndexError) as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': f"Row in '{table_name}' updated successfully"}), 200

@app.route('/tables/<table_name>/rows/<int:row_index>', methods=['DELETE'])
def delete_row(table_name, row_index):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    dynamic_table = database.tables[table_name]

    try:
        del dynamic_table.rows[row_index]
    except IndexError:
        return jsonify({'error': f"Row index {row_index} not found in '{table_name}'"}), 404

    return jsonify({'message': f"Row in '{table_name}' deleted successfully"}), 200


@app.route('/tables/<table_name>/columns', methods=['POST'])
def add_column(table_name):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    dynamic_table = database.tables[table_name]
    data = request.json

    try:
        dynamic_table.add_column(data.get('column_name'), eval(data.get('column_type')))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': f"Column added to '{table_name}' successfully"}), 201

@app.route('/tables/<table_name>/columns/<column_name>', methods=['DELETE'])
def delete_column(table_name, column_name):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    dynamic_table = database.tables[table_name]

    try:
        dynamic_table.delete_column(column_name)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': f"Column '{column_name}' deleted from '{table_name}' successfully"}), 200

@app.route('/tables/<table_name>/remove_duplicates', methods=['POST'])
def remove_duplicates(table_name):
    if table_name not in database.tables:
        return jsonify({'error': f"Table '{table_name}' not found"}), 404

    dynamic_table = database.tables[table_name]

    try:
        dynamic_table.remove_duplicates()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': f"Duplicates removed from '{table_name}' successfully"}), 200

table_info = [
    ("Name", str),
    ("Age", int),
    ("City", str),
    ("IsStudent", bool)
]

table = DynamicTable(table_info)

table.add_row(["Alice", 25, "New York", False])
table.add_row(["Bob", 30, "San Francisco", True])
table.add_row(["Alice", 25, "New York", False])
table.add_row(["Charlie", 22, "Los Angeles", True])

table.display_table()

database.tables["Table1"] = table

if __name__ == '__main__':
    app.run(debug=True)
