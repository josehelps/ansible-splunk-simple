ansible-splunk-simple
==============

Simple deployment for Ansible, static host lists. 

## TODOs

* read me for each role
* update common role base on group vars 
* add roles to ansible galaxy
* make splunk not run under root

## Expectations

This ansible package expectes your servers to be ubuntu base OS. The splunk binaries currently set are *Splunk 6.1.1* located under
`splunk_binaries`

## Installing Ansible

* git clone ansible from `https://github.com/ansible/ansible`

## Ansible Structure

## Roles Details

## Running for the First Time

* Make sure you generate your own set of splunk-admin keys for the splunk-admin user. I have included some as an example but *I recommend you to generate your own using `ssh-keygen`*

## Splunk Account Information
username: admin 
password: buttercup
*https://...*

credentials are stored under playbooks/splunk\_creds 
The cert/key pair deployed are in the same folder. Although I highly recommend you generate your on keypairs
