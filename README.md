# duo-scripts

this repo is for the scripts I have to made solve issues I have run into with Duo user provisioning. 

The add users script parses a csv file of net new users and send out invites to their external email address. This is useful because when using the Duo Directory IdP, there is no good way to send an enrollment link to a new employee since they do not have a corprate account yet. This script will send the email to their external email they used to interview and then change the primary email from their external one to their new company. It will then send a new email with an explanation of the duo email and their user information along with a way to access company applications. In short, they will get two emails, one from Duo to enroll and one from the company explaining the process and providing their email address because the Duo invite does not provide their email address or username. 

The add groups script attaches groups to users based on the department they are in, the groups need to be defined in an object/dictionary.
