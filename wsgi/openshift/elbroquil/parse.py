import xlrd

# import the logging library
import logging
# Get an instance of a logger
logger = logging.getLogger("MYAPP")

def parse_cal_rosset(book):
    sheet = book.sheet_by_index(0)
    products = []
    row_count = sheet.nrows
    col_count = sheet.ncols
    
    current_row = 0

    # Skip to header row
    while True:
        #logger.error(current_row)
        #logger.error(sheet.cell_value(rowx=current_row, colx=4))
        if sheet.cell_value(rowx=current_row, colx=4) == "PRODUCTE":
            current_row += 1
            break
    
        current_row += 1

    empty_rows = 0
    category_name = ""

    while True:
        # If there are many empty rows, end of data
        if empty_rows == 3:
            break;
    
        # If cell empty, it is another empty row
        if sheet.cell_value(rowx=current_row, colx=4) == "":
            empty_rows += 1
            category_name = ""
        else:
            # If cell has data and it's the first data after empty rows, it is category name
            if empty_rows > 0:
                empty_rows = 0
                category_name = sheet.cell_value(rowx=current_row, colx=4)
                #logger.error("CATEGORY: ")
                #logger.error(category_name)
            # Else it is product info
            else:
                product = [category_name, sheet.cell_value(rowx=current_row, colx=4), sheet.cell_value(rowx=current_row, colx=2), sheet.cell_value(rowx=current_row, colx=3), sheet.cell_value(rowx=current_row, colx=5), sheet.cell_value(rowx=current_row, colx=6)]
                #logger.error("PRODUCT: ")
                #logger.error(product)
                #print "PRODUCT:", product
                products.append(product)
    
    
        current_row += 1
    
    return products
        
def parse_can_pipirimosca(book):
    sheet = book.sheet_by_name('Comanda - TOTALS')
    products = []
    row_count = sheet.nrows
    col_count = sheet.ncols
    
    current_row = 0
    
    # Skip to header row
    while True:
        #print current_row, sheet.cell_value(rowx=current_row, colx=1)
        if sheet.cell_value(rowx=current_row, colx=1) == "Productes":
            current_row -= 2
            break
    
        current_row += 1

    empty_rows = 0
    category_name = ""

    while True:
        # If there are many empty rows, end of data
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
                if sheet.cell_value(rowx=current_row, colx=2) != "":
                    product = [category_name, sheet.cell_value(rowx=current_row, colx=1), sheet.cell_value(rowx=current_row, colx=2), sheet.cell_value(rowx=current_row, colx=3), None, None]
                    #print "PRODUCT: ", product
                    products.append(product)
    
    
        current_row += 1
    return products
    
if __name__=="__main__":
    book = xlrd.open_workbook('/Users/onur/Desktop/excel/pan.xlsx')
    print parse_can_pipirimosca(book)
    
#print "The number of worksheets is", book.nsheets
#print "Worksheet name(s):", book.sheet_names()
