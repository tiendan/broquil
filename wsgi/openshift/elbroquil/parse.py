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

from django.utils.translation import ugettext as _
import re

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
    
    # Do some checks on the dates if they were provided
    if distribution_date != "":
        if (type(distribution_date) is not str and type(distribution_date) is not unicode) or (type(order_limit_date) is not str and type(order_limit_date) is not unicode):
            raise ValueError(_(u"Distribution date and order limit date should be in text format!" + type(distribution_date).__name__ + ", " + type(order_limit_date).__name__))

        r = re.compile('([0-9]){4}-([0-9]){2}-([0-9]){2}')

        if r.match(distribution_date) is None or r.match(order_limit_date) is None:
            raise ValueError(_(u"Distribution date and order limit date should be in YYYY-MM-DD format!"))
        
        if order_limit_date:
            order_limit_date += " " + str(sheet.cell_value(rowx=5, colx=1)).zfill(2) + ":00"

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

# When script is executed directly from command line, try to parse a sample Excel file
if __name__=="__main__":
    book = xlrd.open_workbook('/Users/onur/problem1.xlsx')
    print parse_standard(book)
