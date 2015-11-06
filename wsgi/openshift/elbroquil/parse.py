import xlrd
from xlutils.copy import copy
import os
from openpyxl import Workbook
from openpyxl import load_workbook

from oauth2client.client import SignedJwtAssertionCredentials
from httplib2 import Http
from apiclient.discovery import build
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

import json

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
                price = sheet.cell_value(rowx=current_row, colx=price_column)
                origin = sheet.cell_value(rowx=current_row, colx=origin_column)

                # Add VAT depending on product (10% for processed food, 4% for others)
                if "elaborat" in origin.lower() or "elaborad" in origin.lower():
                    price = price * 1.10
                else:
                    price = price * 1.04

                product = [category_name, sheet.cell_value(rowx=current_row, colx=product_name_column), price, sheet.cell_value(rowx=current_row, colx=unit_column), origin, sheet.cell_value(rowx=current_row, colx=comments_column)]

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

def parse_standard(book):
    # Define the corresponding column numbers in Excel sheet for each type of information
    category_column = 0
    product_name_column = 1
    price_column = 2
    unit_column = 3
    origin_column = 4
    comments_column = 5
    unit_demand_column = 6

    # Get the first sheet and read row and column counts
    sheet = book.sheet_by_index(0)
    products = []
    row_count = sheet.nrows
    col_count = sheet.ncols

    current_row = 10

    empty_rows = 0
    category_name = ""
    unit_name = ""

    # Read distribution date and order limit date&hour info
    distribution_date = sheet.cell_value(rowx=3, colx=1)
    order_limit_date = sheet.cell_value(rowx=4, colx=1)

    if order_limit_date:
        order_limit_date += " " + str(sheet.cell_value(rowx=5, colx=1)) + ":00"

    # Loop over the sheet rows
    while current_row < row_count:
        # If cell empty, it is another empty row
        if sheet.cell_value(rowx=current_row, colx=product_name_column) == "":
            empty_rows += 1
            category_name = ""
        else:
            empty_rows = 0

            # If category name is filled, update it. Otherwise, use the previous category name
            category_name = sheet.cell_value(rowx=current_row, colx=category_column).strip() or category_name
            # If unit is filled, update it. Otherwise, use the previous unit
            unit_name = sheet.cell_value(rowx=current_row, colx=unit_column).strip() or unit_name

            product = [category_name, sheet.cell_value(rowx=current_row, colx=product_name_column), sheet.cell_value(rowx=current_row, colx=price_column), unit_name, sheet.cell_value(rowx=current_row, colx=origin_column), sheet.cell_value(rowx=current_row, colx=comments_column), sheet.cell_value(rowx=current_row, colx=unit_demand_column)]

            products.append(product)

        current_row += 1

    return products, distribution_date, order_limit_date

# Parse the excel for Can Perol producer
def parse_can_perol(filename):
    print "Parsing Can Perol format"

    # Directory where to find the private key
    data_dir = '/Users/onur/github/broquil/data/'

    if os.environ.has_key('OPENSHIFT_DATA_DIR'):
        data_dir = os.path.join(os.environ['OPENSHIFT_DATA_DIR'], "temp")

    # First upload and download the XLS file to convert as xlsx
    # Setup the connection to Google Drive API
    client_email = '975533004012-d4veh1666grh6es8bq0celae34u9ag7k@developer.gserviceaccount.com'
    with open(os.path.join(data_dir, "serviceaccount.json")) as f:
        private_key = json.load(f)['private_key']

    credentials = SignedJwtAssertionCredentials(client_email, private_key,
        ['https://www.googleapis.com/auth/sqlservice.admin', 'https://www.googleapis.com/auth/drive'])

    http_auth = credentials.authorize(Http())
    service = build('drive', 'v2', http=http_auth)
    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive = GoogleDrive(gauth)

    uploaded_file = drive.CreateFile({'title': 'dummyfile.xls'})
    uploaded_file.SetContentFile(filename)
    uploaded_file.Upload({'convert': True})

    download_url = uploaded_file['exportLinks']['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    converted_filename = filename + '.xlsx'

    if download_url:
        resp, content = service._http.request(download_url)
        if resp.status == 200:
            with open(converted_filename, 'wb') as f:
                f.write(content)
        else:
            print 'An error occurred: %s' % resp

    # Open converted book
    book = load_workbook(converted_filename, use_iterators=True)
    sheet = book.active

    ## PARSING ##

    # Define the corresponding column numbers in Excel sheet for each type of information
    origin_column = 1
    product_name_column = 3
    unit_column = 4
    price_column = 6
    quantity_column = 7
    vat_column = 10

    # Get the first sheet and read row and column counts
    products = []
    #row_count = sheet.nrows

    current_row = 1

    # Skip to header row
    # Header row contains "Origen" in the origin column
    while True:
        if sheet.cell(row=current_row, column=origin_column).value == "Origen":
            break
        current_row += 1

    empty_rows = 1
    category_name = ""

    last_vat_multiplier = 1

    # Loop over the sheet rows
    while True:
        # If there are many (5) consecutive empty rows, we have reached the end of data
        if empty_rows == 5:
            break;
        # If cell empty, it is another empty row
        if sheet.cell(row=current_row, column=product_name_column).value == "" or sheet.cell(row=current_row, column=product_name_column).value is None:
            empty_rows += 1
            category_name = ""
        else:
            # If cell has data and it's the first data after few empty rows, it is category name
            if empty_rows > 0:
                empty_rows = 0
                category_name = sheet.cell(row=current_row, column=product_name_column).value
                #print "New category:", category_name
            # Else it is product info
            else:
                # If it is subcategory, skip it
                if sheet.cell(row=current_row, column=origin_column).value == "Origen":
                    pass
                else:
                    # Create the array containing product info and append it to product list
                    product_name = sheet.cell(row=current_row, column=product_name_column).value
                    #price = sheet.cell(row=current_row, column=price_column)
                    origin = sheet.cell(row=current_row, column=origin_column).value
                    # Add VAT depending on product (10% for processed food, 4% for others)
                    price = sheet.cell(row=current_row, column=price_column).value
                    vat_multiplier_cell = sheet.cell(row=current_row, column=vat_column).value
                    vat_multiplier = None

                    try:
                        # Extract VAT multiplier from possible formula
                        if vat_multiplier_cell is None:
                            pass
                        elif vat_multiplier_cell == "=":
                            pass
                        else:
                            vat_multiplier = float(vat_multiplier_cell.split('=')[-1].split("*")[-1])
                    except:
                        pass

                    if vat_multiplier is None:
                        vat_multiplier = last_vat_multiplier
                    else:
                        last_vat_multiplier = vat_multiplier

                    # Update the price with VAT information
                    price = price * last_vat_multiplier

                    product = [category_name, product_name, price, sheet.cell(row=current_row, column=unit_column).value, origin, ""]

                    # Do not add products from some categories
                    if "carnisseria" in category_name.lower() or "algues" in category_name.lower() or "prote" in category_name.lower() or "fleca" in category_name.lower() or "cereals" in category_name.lower():
                        pass
                    else:
                        products.append(product)
        current_row += 1

    return products

# When script is executed directly from command line, try to parse a sample Excel file
if __name__=="__main__":
    #book = xlrd.open_workbook('/Users/onur/canperolDOWNLOAD.xlsx')
    print parse_can_perol('/Users/onur/canperol.xls')
