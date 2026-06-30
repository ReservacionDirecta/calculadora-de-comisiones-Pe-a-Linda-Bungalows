with open('sirvoy.csv', 'r') as f:
    lines = f.readlines()
    print(f'Total lines: {len(lines)}')
    print(f'First line (headers): {lines[0].strip()}')
    print(f'Second line (sample data): {lines[1].strip()}')
    print(f'Number of columns in header: {len(lines[0].split(","))}')
    print(f'Number of columns in data: {len(lines[1].split(","))}')
