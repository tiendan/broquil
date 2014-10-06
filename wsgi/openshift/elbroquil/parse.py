import xlrd

# import the logging library
#import logging
# Get an instance of a logger
#logger = logging.getLogger("MYAPP")

# Parse the excel for Cal Rosset producer
def parse_cal_rosset(book):
    # Define the corresponding column numbers in Excel sheet for each type of information
    price_column = 3
    unit_column = 4
    product_name_column = 5
    origin_column = 6
    comments_column = 8
    
    # Get the first sheet and read row and column counts
    sheet = book.sheet_by_index(0)
    products = []
    row_count = sheet.nrows
    col_count = sheet.ncols
    
    current_row = 0

    # Skip to header row
    # Header row contains "Coop." for in the price column
    while True:
        #logger.error(current_row)
        #logger.error(sheet.cell_value(rowx=current_row, colx=4))
        if sheet.cell_value(rowx=current_row, colx=price_column) == "Coop.":
            current_row += 1
            break
    
        current_row += 1

    empty_rows = 0
    category_name = ""

    # Loop over the sheet rows
    while True:
        # If there are many (3) consecutive empty rows, we have reached the end of data
        if empty_rows == 3:
            break;
        
        # If cell empty, it is another empty row
        if sheet.cell_value(rowx=current_row, colx=product_name_column) == "":
            empty_rows += 1
            category_name = ""
        else:
            # If cell has data and it's the first data after few empty rows, it is category name
            if empty_rows > 0:
                empty_rows = 0
                category_name = sheet.cell_value(rowx=current_row, colx=product_name_column)
                #logger.error("CATEGORY: ")
                #logger.error(category_name)
            # Else it is product info
            else:
                # Create the array containing product info and append it to product list
                product = [category_name, sheet.cell_value(rowx=current_row, colx=product_name_column), sheet.cell_value(rowx=current_row, colx=price_column), sheet.cell_value(rowx=current_row, colx=unit_column), sheet.cell_value(rowx=current_row, colx=origin_column), sheet.cell_value(rowx=current_row, colx=comments_column)]
                
                #logger.error("PRODUCT: ")
                #logger.error(product)
                #print "PRODUCT:", product
                
                products.append(product)
    
    
        current_row += 1
    
    return products

# Parse the excel for Can Pipirimosca producer
def parse_can_pipirimosca(book):
    # Get the sheet with product information and read row and column counts
    sheet = book.sheet_by_name('Comanda')
    products = []
    row_count = sheet.nrows
    col_count = sheet.ncols
    
    current_row = 0
    
    # Skip to header row
    # Header row contains "Productes" for in the price column
    while True:
        #print current_row, sheet.cell_value(rowx=current_row, colx=1)
        if sheet.cell_value(rowx=current_row, colx=1) == "Productes":
            current_row -= 2
            break
    
        current_row += 1

    empty_rows = 0
    category_name = ""

    while True:
        # If there are many (3) consecutive empty rows, we have reached the end of data
        if empty_rows == 10:
            break;
    
        # If cell empty, it is another empty row
        if sheet.cell_value(rowx=current_row, colx=1) == "":
            empty_rows += 1
        else:
            # If cell has data and it's the first data after empty rows, it is category name
            if sheet.cell_value(rowx=current_row, colx=1) == "Productes":
                empty_rows = 0
                category_name = sheet.cell_value(rowx=current_row-1, colx=1)
                #print "CATEGORY: ", category_name
            # Else it is product info
            else:
                # Create the array containing product info and append it to product list
                if sheet.cell_value(rowx=current_row, colx=2) != "":
                    product = [category_name, sheet.cell_value(rowx=current_row, colx=1), sheet.cell_value(rowx=current_row, colx=2), sheet.cell_value(rowx=current_row, colx=3), None, None]
                    #print "PRODUCT: ", product
                    products.append(product)
    
    
        current_row += 1
    return products
    
# When script is executed directly from command line, try to parse a sample Excel file
if __name__=="__main__":
    book = xlrd.open_workbook('/Users/onur/Desktop/excel/pan.xlsx')
    print parse_can_pipirimosca(book)
    
