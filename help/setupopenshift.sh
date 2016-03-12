#!/bin/bash

# Fully automatical installation script for Mac OS X and Linux systems.
# It will pull the Broquil project from GitHub and install a copy of it on your OpenShift account.
# 
# Before starting, complete the following steps:
#
# 1) Create an account in Gmail (https://www.gmail.com/)
# 2) Configure your Gmail account settings:
#    a) Set up 2-Step Verification and verify your mobile phone number (https://myaccount.google.com/security)
#    b) Go to "App-specific Passwords" tab and enter "Manage application specific passwords" (https://accounts.google.com/b/0/SmsAuthSettings#asps)
#    c) Select "Custom" as application and give a custom name, and generate
#    d) Save the 16-digit password aside (gfheltxgjvbkeomi)
#    
# 3) Create an account in OpenShift (https://www.openshift.com/)
# 4) Set up your domain name in OpenShift settings
# 5) Install the OpenShift Client Tools (https://developers.openshift.com/en/managing-client-tools.html#_select_your_operating_system)
# 6) Install Git SCM (https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

# --------------------------------------------------
# ----------------- FILL THIS PART -----------------
# --------------------------------------------------
# After these steps, fill in the following information
EMAIL_ADDRESS=GMAILACCOUNT@gmail.com        # The Gmail account you created in step 1 above
EMAIL_PASSWORD=16DIGITPASSWORD              # The app-specific password you created in step 2-d above
OPENSHIFT_PASSWORD=OPENSHIFTPASSWORD        # The password for your OpenShift account you created in step 3
OPENSHIFT_DOMAIN=OPENSHIFT_DOMAIN_NAME      # The domain name for your OpenShift account as created in step 4
OPENSHIFT_APP_NAME=OPENSHIFT_APPLICATION_NAME   # The preferred name for your application. 
# --------------------------------------------------
# ------------------- UNTIL HERE -------------------
# --------------------------------------------------




# --------------------------------------------------
# ----------- DON'T TOUCH ANYTHING BELOW -----------
# ------ IF YOU DON'T KNOW WHAT YOU ARE DOING ------
# --------------------------------------------------

# 1) Configure the OpenShift client tools with the OpenShift account details
yes | rhc setup -l $EMAIL_ADDRESS -p $OPENSHIFT_PASSWORD --server openshift.redhat.com


# 2) Create a new app in OpenShift, and add the required gears (Python, MySQL, phpMyAdmin and cron)
yes | rhc app create $OPENSHIFT_APP_NAME python-2.7 mysql-5.5 phpmyadmin cron-1.4


# 3) Get the ID for the newly created application
OPENSHIFT_APP_ID=`rhc app-show $OPENSHIFT_APP_NAME | grep "(uuid:" | awk 'match($0, /\(uuid:(.*)\)/) {print substr($0, RSTART+7, RLENGTH-8)}'`


# 4) TODO Get the tiendan/broquil repository from GitHub
git clone -b generic --single-branch https://github.com/tiendan/broquil.git generic

# 5) TODO CD into the project folder
cd generic

# 6) Add the OpenShift remote repository to git configuration
git remote add openshift ssh://$OPENSHIFT_APP_ID@$OPENSHIFT_APP_NAME-$OPENSHIFT_DOMAIN.rhcloud.com/~/git/$OPENSHIFT_APP_NAME.git/


# 7) Set the environment variables for the new application (email user and password information)
rhc env set EMAIL_HOST_USER=$EMAIL_ADDRESS EMAIL_HOST_PASSWORD=$EMAIL_PASSWORD -a $OPENSHIFT_APP_NAME


# 8) Push the project's generic branch to OpenShift
git push -f openshift generic:master


# 9) Connect to the OpenShift application through SSH and create the super user and insert the Site record
init_script=''
init_script=$init_script'from django.contrib.auth.models import User;'
init_script=$init_script'from django.contrib.sites.models import Site;'
init_script=$init_script'User.objects.create_superuser("admin", "'$EMAIL_ADDRESS'", "'$OPENSHIFT_PASSWORD'");'
init_script=$init_script'Site(name="Openshift", domain="'$OPENSHIFT_APP_NAME'-'$OPENSHIFT_DOMAIN'.rhcloud.com").save();'

# Calculate the next dates for some of the jobs
DAY_OF_WEEK=`date +%u`
NEXT_THURSDAY=4

if [ $DAY_OF_WEEK -gt $NEXT_THURSDAY ]
then
    NEXT_THURSDAY=11
fi

NEXT_SATURDAY=$(($NEXT_THURSDAY+2))

DAYS_TO_THURSDAY=$(($NEXT_THURSDAY-$DAY_OF_WEEK))
DAYS_TO_SATURDAY=$(($NEXT_SATURDAY-$DAY_OF_WEEK))

if [[ "$(uname)" == "Linux" ]] ; then
    thursday=`date -d "$DAYS_TO_THURSDAY days" +%Y-%m-%d`
    saturday=`date -d "$DAYS_TO_SATURDAY days" +%Y-%m-%d`
elif [[ "$(uname)" == "Darwin" ]] ; then
    thursday=`date -j -v+${DAYS_TO_THURSDAY}d +"%Y-%m-%d"`
    saturday=`date -j -v+${DAYS_TO_SATURDAY}d +"%Y-%m-%d"`
fi

# Add Django code to insert the jobs for several tasks
init_script=$init_script'from chroniker.models import Job;'
init_script=$init_script'from django.utils.dateparse import *;'
init_script=$init_script'from pytz import timezone as pytztimezone;'
init_script=$init_script'import settings;'

init_script=$init_script'zone = pytztimezone(settings.TIME_ZONE);'

init_script=$init_script'thursday = parse_datetime("'$thursday' 15:00");'
init_script=$init_script'saturday = parse_datetime("'$saturday' 20:00");'

init_script=$init_script'thursday = zone.localize(datetime.datetime(thursday.year, thursday.month, thursday.day, thursday.hour), is_dst=False);'
init_script=$init_script'thursday = thursday.astimezone(pytztimezone("UTC"));'

init_script=$init_script'saturday = zone.localize(datetime.datetime(saturday.year, saturday.month, saturday.day, saturday.hour), is_dst=False);'
init_script=$init_script'saturday = saturday.astimezone(pytztimezone("UTC"));'
            
init_script=$init_script'Job(name="Send order to producer", frequency="MINUTELY", params="interval:10", command="sendordertoproducers", maximum_log_entries=100, log_stderr=1).save();'
init_script=$init_script'Job(name="Send reminder emails", frequency="WEEKLY", command="sendreminder", maximum_log_entries=100, log_stderr=1, next_run=saturday).save();'
init_script=$init_script'Job(name="Create weekly product offer", frequency="WEEKLY", command="createoffer", maximum_log_entries=100, log_stderr=1, next_run=thursday).save();'
init_script=$init_script'Job(name="Clear expired sessions", frequency="DAILY", command="clearsessions", maximum_log_entries=100, log_stderr=1).save();'

# Execute the prepared script through SSH
ssh $OPENSHIFT_APP_ID@$OPENSHIFT_APP_NAME-$OPENSHIFT_DOMAIN.rhcloud.com << EOF
    cd app-root/repo/
    echo '$init_script' | python wsgi/openshift/manage.py shell
EOF

