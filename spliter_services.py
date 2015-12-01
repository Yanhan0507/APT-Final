#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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
#

__author__ = 'henry'

import webapp2
from constants import *
import logging, json
import uuid
from datetime import datetime
from model import User, Apartment, Expense, Item, Note, NoteBook

class ServiceHandler(webapp2.RequestHandler):
    def respond(self, separators=(',', ':'), **response):
        if KEYWORD_ERROR in response and response[KEYWORD_ERROR]:
            #   record the error msg
            logging.error("Web Service Error: " + response[KEYWORD_ERROR])
        elif KEYWORD_STATUS in response:
            #   record the debugging status
            logging.debug("Web Service Debugging Information: " + response[KEYWORD_STATUS])

        if IDENTIFIER_JSON_MSG in self.request.headers.get('Accept'):
            self.response.headers['Content-Type'] = IDENTIFIER_JSON_MSG

        return self.response.write(json.dumps(response, separators=separators))


class CreateAccountService(ServiceHandler):
    def post(self):

        req_json = json.loads(self.request.body)


        user_email = req_json[IDENTIFIER_USER_EMAIL]

        # check whether this email has been used or not
        users = User.query(User.user_email == user_email).fetch()
        if len(users) > 0:
            response = {}
            response['error'] = 'the email: ' + user_email + ' has already been used'
            return self.respond(**response)

        nick_name = req_json[IDENTIFIER_NICE_NAME]
        # bank_account and user photo are not required
        bank_account = None
        cover_url = None
        if IDENTIFIER_BANK_ACCOUNT in req_json:
            bank_account = req_json[IDENTIFIER_BANK_ACCOUNT]
        if IDENTIFIER_USER_PHOTO in req_json:
            cover_url = req_json[IDENTIFIER_USER_PHOTO]

        new_user = User(user_email = user_email,
                        nick_name = nick_name,
                        bank_account = bank_account,
                        cover_url = cover_url,
                        owe = INITIAL_BALANCE
                        )

        new_user.put()
        print 'Successfully created new user:' + user_email
        self.respond(user_email=user_email, status="Success")

class CreateAptService(ServiceHandler):
    def post(self):
        apt_id = uuid.uuid4()
        req_json = json.loads(self.request.body)

        apt_name = req_json[IDENTIFIER_APT_NAME]
        user_email = req_json[IDENTIFIER_USER_EMAIL]

        user_email_lst = req_json[IDENTIFIER_USER_EMAIL_LIST]
        user_email_lst.insert(0, user_email)

        cover_url = None
        if IDENTIFIER_APT_PHOTO in req_json:
            cover_url = req_json[IDENTIFIER_APT_PHOTO]

        # check whether all of these email are valid users
        for user in user_email_lst:
            user = user.encode('utf8')
            users = User.query(User.user_email == user).fetch()
            if len(users) == 0:
                response = {}
                response['error'] = 'the email: ' + user + ' has not been registered'
                return self.respond(**response)
            if users[0].apt_id is not None:
                response = {}
                response['error'] = 'the email: ' + user + ' has already joined other apartment'
                return self.respond(**response)


        for user in user_email_lst:
            users = User.query(User.user_email == user).fetch()
            cur_user = users[0]
            cur_user.apt_id = str(apt_id)
            cur_user.put()

        note_book_id = uuid.uuid4()
        new_note_book = NoteBook(notebook_id = str(note_book_id),
                                 apt_id = str(apt_id))
        new_note_book.put()

        new_apt = Apartment(apt_id = str(apt_id),
                            apt_name = apt_name,
                            creater_email = user_email,
                            user_email_lst = user_email_lst,
                            cover_url = cover_url,
                            notebook_id = str(note_book_id))
        new_apt.put()

        self.respond(apt_id = str(apt_id), status="Success")




class CreateExpenseService(ServiceHandler):
    def post(self):
        expense_id = uuid.uuid4()
        req_json = json.loads(self.request.body)

        expense_name = req_json[IDENTIFIER_EXPENSE_NAME ]
        user_email = req_json[IDENTIFIER_USER_EMAIL]

        apt_name = req_json[IDENTIFIER_APT_NAME]

        target_apt_lst = Apartment.query(Apartment.apt_name == apt_name).fetch()

        target_apt = None

        for apt in target_apt_lst:
            if user_email in apt.user_email_lst:
                target_apt = apt
                break
        if target_apt == None:
            response = {}
            response['error'] = 'the user: ' + user_email + ' is not valid for apt: ' + apt_name
            return self.respond(**response)

        user_email_lst = req_json[IDENTIFIER_USER_LIST ]
        user_email_lst.insert(0, user_email)


        # check whether this apt name is valid or not
        expense_lst = Expense.query(Expense.expense_name == expense_name)
        for expense in expense_lst:
            for user in user_email_lst:
                if user in expense.user_email_lst:
                    response = {}
                    response['error'] = 'the apartment name: ' + expense_name + ' has not been used for ' + user
                    return self.respond(**response)

        # check whether all of these email are valid users
        for user in user_email_lst:
            users = User.query(User.user_email == user).fetch()
            if len(users) == 0:
                response = {}
                response['error'] = 'the email: ' + user + ' has not been registered'
                return self.respond(**response)



        cover_url = None
        if IDENTIFIER_APT_PHOTO in req_json:
            cover_url = req_json[IDENTIFIER_APT_PHOTO]


        new_expense = Expense(apt_id = target_apt.apt_id,
                              creater_email = user_email,
                              user_email_lst = user_email_lst,
                              cover_url = cover_url,
                              expense_name = expense_name,
                              total_cost = 0,
                              is_paid = False,
                              expense_id = str(expense_id ))

        target_apt.expense_id_lst.insert(0, str(expense_id))
        new_expense.put()
        target_apt.put()
        self.respond(expense_id = str(expense_id), status="Success")


class CreateItemService(ServiceHandler):
    def post(self):
        item_id = uuid.uuid4()
        req_json = json.loads(self.request.body)

        item_name = req_json[IDENTIFIER_ITEM_NAME]
        expense_name = req_json[IDENTIFIER_EXPENSE_NAME]
        buyer_email = req_json[IDENTIFIER_BUYER_EMAIL]
        sharer_email_lst = req_json[IDENTIFIER_SHARER_LIST]

        expense_lst = Expense.query(Expense.expense_name == expense_name)
        expense_id = None

        total_cost = float(req_json[IDENTIFIER_TOTAL_COST])
        target_expense = None
        cover_url = None
        if IDENTIFIER_APT_PHOTO in req_json:
            cover_url = req_json[IDENTIFIER_APT_PHOTO]

        for expense in expense_lst:
            if buyer_email in expense.user_email_lst:
                expense_id = expense.expense_id
                target_expense = expense
                break

        if expense_id == None:
            response = {}
            response['error'] = 'the buyer email: ' + buyer_email + ' is not valid for this expense/apartment'
            return self.respond(**response)

        new_item = Item(item_id = str(item_id),
                        item_name = item_name,
                        cover_url = cover_url,
                        expense_id = expense_id,
                        buyer_email = buyer_email,
                        sharer_email_lst = sharer_email_lst,
                        total_cost = total_cost
                        )
        new_item.put()
        target_expense.item_id_lst.insert(0, str(item_id))
        target_expense.total_cost += total_cost
        target_expense.put()


        self.respond(item_id_id = str(item_id), status="Success")



class addUserToAptService(ServiceHandler):
    def post(self):

        req_json = json.loads(self.request.body)

        apt_name = req_json[IDENTIFIER_APT_NAME]
        user_email = req_json[IDENTIFIER_USER_EMAIL]
        new_email = req_json[IDENTIFIER_NEW_EMAIL]

        apt_lst = Apartment.query(Apartment.apt_name == apt_name)
        target_apt = None

        for apt in apt_lst:
            if user_email in apt.user_email_lst:
                target_apt = apt
                break
        user_lst = User.query(User.user_email == new_email).fetch()

        if target_apt == None:
            response = {}
            response['error'] = 'the email: ' + user_email + ' has not been registered'
            return self.respond(**response)
        if len(user_lst) == 0:
            response = {}
            response['error'] = 'the new email: ' + new_email + ' has not been registered'
            return self.respond(**response)

        new_user = user_lst[0]

        if not new_user.apt_id is None:
            response = {}
            response['error'] = 'the user: ' + new_email + ' cannot be added'
            return self.respond(**response)

        new_user.apt_id = target_apt.apt_id
        if not new_email in target_apt.user_email_lst:
            target_apt.user_email_lst.insert(0, new_email)
            target_apt.put()
        new_user.put()

        self.respond(apt_id = target_apt.apt_id, status="Success")


class addUserToExpenseService(ServiceHandler):
    def post(self):

        req_json = json.loads(self.request.body)
        expense_name = req_json[IDENTIFIER_EXPENSE_NAME]
        user_email = req_json[IDENTIFIER_USER_EMAIL]
        new_sharer_email = req_json[IDENTIFIER_NEW_EMAIL]

        target_expense = None

        expense_lst = Expense.query(Expense.expense_name == expense_name)

        for expense in expense_lst:
            if user_email in expense.user_email_lst:
                target_expense = expense
                break

        if target_expense == None:
            response = {}
            response['error'] = 'the expense: ' + expense_name + ' has not been created'
            return self.respond(**response)



        if not new_sharer_email in target_expense.user_email_lst:
            target_expense.user_email_lst.insert(0, new_sharer_email)

        target_expense.put()

        self.respond(expense_id = target_expense.expense_id,
                     new_user = new_sharer_email, status="Success")


class checkSingleExpenseService(ServiceHandler):
    def get(self):

        expense_name = self.request.get(IDENTIFIER_EXPENSE_NAME)
        apt_name = self.request.get(IDENTIFIER_APT_NAME)
        user_email = self.request.get(IDENTIFIER_USER_EMAIL)
        apt_lst = Apartment.query(Apartment.apt_name == apt_name).fetch()

        cur_apt = None
        for apt in apt_lst:
            if user_email in apt.user_email_lst:
                cur_apt = apt

        if cur_apt == None:
            response = {}
            response['error'] = 'the apt: ' + apt_name + ' is not available for user: ' + user_email
            return self.respond(**response)

        expense_lst = Expense.query(Expense.expense_name == expense_name).fetch()
        cur_expense = None
        for expense in expense_lst:
            if expense.apt_id == cur_apt.apt_id:
                cur_expense = expense

        if cur_expense == None:
            response = {}
            response['error'] = 'the apt: ' + apt_name + ' does not have a expense named: ' + expense_name
            return self.respond(**response)
        if cur_expense.is_paid:
            response = {}
            response['error'] = 'the : ' + expense_name + ' has already been paid'
            return self.respond(**response)
        cur_expense.checkout()
        self.respond(status="Success")

class checkAllExpenseService(ServiceHandler):
    def get(self):
        apt_name = self.request.get(IDENTIFIER_APT_NAME)
        user_email = self.request.get(IDENTIFIER_USER_EMAIL)
        apt_lst = Apartment.query(Apartment.apt_name == apt_name).fetch()
        cur_apt = None
        for apt in apt_lst:
            if user_email in apt.user_email_lst:
                cur_apt = apt
        if cur_apt == None:
            response = {}
            response['error'] = 'the apt: ' + apt_name + ' is not available for user: ' + user_email
            return self.respond(**response)

        for expense_id in cur_apt.expense_id_lst:
            expense_lst = Expense.query(Expense.expense_id == expense_id).fetch()
            if len(expense_lst) > 0:
                expense = expense_lst[0]
                if not expense.is_paid:
                    expense.checkout()

        self.respond(status="Success")


class getPaymentService(ServiceHandler):
    def get(self):
        apt_name = self.request.get(IDENTIFIER_APT_NAME)
        user_email = self.request.get(IDENTIFIER_USER_EMAIL)
        apt_lst = Apartment.query(Apartment.apt_name == apt_name).fetch()

        # print "called: " + user_email + ", " + apt_name
        cur_apt = None
        for apt in apt_lst:
            if user_email in apt.user_email_lst:
                cur_apt = apt

        user_lst = User.query(User.apt_id == cur_apt.apt_id).fetch()

        sorted_user_lst = sorted(user_lst, key=lambda user:user.owe)

        first = 0
        end = len(sorted_user_lst) - 1

        payment_lst = []

        print "sorted_lst: " + str(sorted_user_lst)

        while first < end:
            first_user = sorted_user_lst[first]
            end_user = sorted_user_lst[end]
            if first_user.owe == 0:
                first += 1
                continue
            if end_user.owe == 0:
                end -= 1
                continue
            payment = {}

            payment['from'] = first_user.user_email
            payment['to'] = end_user.user_email



            if abs(first_user.owe) > end_user.owe:
                payment['amount'] = end_user.owe
                first_user.owe += end_user.owe
                end_user.owe = 0

            else:
                payment['amount'] = abs(first_user.owe)
                end_user.owe -= abs(first_user.owe)
                first_user.owe = 0


            print payment
            print first_user.user_email + ": " + str(first_user.owe)
            print end_user.user_email + ": " + str(end_user.owe)

            payment_lst.append(payment)
            first_user.put()
            end_user.put()

        self.respond(payment_lst = payment_lst, status="Success")



class addNoteService(ServiceHandler):
    def post(self):

        req_json = json.loads(self.request.body)
        user_email = req_json[IDENTIFIER_USER_EMAIL]
        apt_name = req_json[IDENTIFIER_APT_NAME]
        description = req_json[IDENTIFIER_DESCRIPTION_NAME]

        apt_lst = Apartment.query(Apartment.apt_name == apt_name).fetch()

        cur_apt = None
        for apt in apt_lst:
            if user_email in apt.user_email_lst:
                cur_apt = apt

        if cur_apt == None:
            response = {}
            response['error'] = 'the apt: ' + apt_name + ' is not available for user: ' + user_email
            return self.respond(**response)

        cur_note_book_id = cur_apt.notebook_id

        cur_note_book_lst = NoteBook.query(NoteBook.notebook_id == cur_note_book_id).fetch()

        if len(cur_note_book_lst) == 0:
            response = {}
            response['error'] = 'we dont have notebook for the apt: ' + apt_name
            return self.respond(**response)

        cur_note_book = cur_note_book_lst[0]

        note_id = uuid.uuid4()
        note = Note(id = str(note_id), description = description, author_email = user_email, notebook_id = cur_note_book_id)

        cur_note_book.note_id_lst.append(str(note_id))

        cur_note_book.put()
        note.put()

        self.respond(note_id = str(note_id), notebook_id = cur_note_book_id, status="Success")



class editNoteService(ServiceHandler):
    def post(self):

        req_json = json.loads(self.request.body)
        user_email = req_json[IDENTIFIER_USER_EMAIL]
        note_id = req_json[IDENTIFIER_NOTE_ID]
        new_description = req_json[IDENTIFIER_NEW_DESCRIPTION_NAME]

        cur_note_lst = Note.query(Note.id == note_id).fetch()

        if len(cur_note_lst) == 0:
            response = {}
            response['error'] = 'the note with id : ' + note_id + ' is valid'
            return self.respond(**response)

        cur_note = cur_note_lst[0]

        if user_email != cur_note.author_email:
            response = {}
            response['error'] = 'you cannot edit this note'
            return self.respond(**response)

        cur_note.description = new_description
        cur_note.put()

        self.respond(status="Success")

class getAllNoteService(ServiceHandler):
    def get(self):
        apt_name = self.request.get(IDENTIFIER_APT_NAME)
        user_email = self.request.get(IDENTIFIER_USER_EMAIL)
        apt_lst = Apartment.query(Apartment.apt_name == apt_name).fetch()

        # print "called: " + user_email + ", " + apt_name
        cur_apt = None
        for apt in apt_lst:
            if user_email in apt.user_email_lst:
                cur_apt = apt

        cur_notebook_lst = NoteBook.query( NoteBook.notebook_id == cur_apt.notebook_id).fetch()
        if len(cur_notebook_lst) == 0:
            response = {}
            response['error'] = 'we dont have notebook for the apt: ' + apt_name
            return self.respond(**response)


        cur_notebook = cur_notebook_lst[0]


        retList = []
        for noteid in cur_notebook.note_id_lst:
            note_lst = Note.query(Note.id == noteid).fetch()
            cur_note = note_lst[0]
            ret_note = {}
            ret_note['author'] = cur_note.author_email
            ret_note['description'] = cur_note.description
            date = str(cur_note.date)
            ret_note['last_edit_date'] = date
            retList.append(ret_note)

        self.respond(AllNoteLst = retList, status="Success")



class getSingleNoteService(ServiceHandler):
    def get(self):

        user_email = self.request.get(IDENTIFIER_USER_EMAIL)
        note_id = self.request.get(IDENTIFIER_NOTE_ID)

        cur_note_lst = Note.query(Note.id == note_id).fetch()

        if len(cur_note_lst) == 0:
            response = {}
            response['error'] = 'The ID is not available: ' + note_id
            return self.respond(**response)

        cur_note = cur_note_lst[0]

        retValue = {}
        retValue['author'] = cur_note.author_email
        retValue['last_edit_date'] = str(cur_note.date)
        retValue['description'] = cur_note.description
        self.respond(Note = retValue, status="Success")



app = webapp2.WSGIApplication([
    ('/createAccount', CreateAccountService),
    ('/createApt', CreateAptService),
    ('/createExpense', CreateExpenseService),
    ('/createItem', CreateItemService),
    ('/addUserToExpense', addUserToExpenseService),
    ('/addUserToApt', addUserToAptService),
    ('/checkSingleExpense',checkSingleExpenseService),
    ('/checkAllExpense', checkAllExpenseService),
    ('/getPayment', getPaymentService),
    ('/addNote', addNoteService),
    ('/editNote' ,editNoteService),
    ('/getAllNote', getAllNoteService),
    ('/getSingleNote', getSingleNoteService)
], debug=True)