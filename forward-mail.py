# -*- coding: utf-8 -*-
import sys
import configparser
import poplib
import email
import smtplib
import os
import datetime

CFG = 'email'


def readOption(config, section, option):
    try:
        return config.get(section, option)
    except configparser.NoOptionError as e:
        return e.message


def test_read_config():
    config_file = "py-forward-mail.ini"
    cfg = configparser.ConfigParser()
    cfg.read(config_file, encoding='UTF-8')

    pop3 = dict(cfg.items('pop3'))

    assert pop3['pop3_host'] == '127.0.0.1'
    assert pop3['xx'] == ""


def get_config(fnames=['email.ini'], section = CFG):
    cfg = configparser.ConfigParser()
    cfg.read(*fnames)
    return {
        'pop3_host': cfg.get(section,'pop3_host'),
        'smtp_host': cfg.get(section,'smtp_host'),
        'username': cfg.get(section,'username'),
        'password':  cfg.get(section,'password'),
        'forward_to': cfg.get(section, 'forward_to'),
        'log_dir': cfg.get(section, 'log_dir')
    }


def forward_mail(smtp_server, mail, forward_to):
    from_mail = email.Header.decode_header(mail['From'])[0][0]
    to_mail = [forward_to,]
    smtp_server.sendmail(from_mail,to_mail,mail.as_string())


def get_all_emails(message_id_set, cfg, debuglevel=0):
    try:
        pop3_host = cfg['pop3_host']
        mail = poplib.POP3(pop3_host)
        mail.set_debuglevel(debuglevel)
        mail.user(cfg['username'])
        mail.pass_(cfg['password'])

        num_messages = mail.stat()[0]
        if num_messages:
            print('{0} new messages'.format(num_messages))
            smtp_server = smtplib.SMTP(cfg['smtp_host'])
            smtp_server.set_debuglevel(debuglevel)
            smtp_server.login(cfg['username'], cfg['password'])
            for i in range(1, num_messages+1):
                text = mail.retr(i)[1]
                mm = email.message_from_string('\n'.join(text))
                from_mail = email.Header.decode_header(mm['From'])[0][0]
                message_id = mm['Message-ID']
                if not message_id in message_id_set :
                    forward_mail(smtp_server, mm, cfg["forward_to"])
                    message_id_set.add(message_id)
                    if from_mail.find('0xLJC6F3D0C5B2BFCAFDBEDDCDA8B1A8z')>=0:
                        print(from_mail + ' delete message\n')
                        mail.dele(i)
                else:
                    print(message_id + '\n')
            smtp_server.quit()
    except poplib.error_proto as e:
        print('Email error:%s' % str(e))
    mail.quit()


def set_to_file(message_id_set, today_file):
    file_output = open(today_file,'w')
    for message_id in message_id_set:
        if message_id:
            file_output.write(message_id + '\n')
    file_output.close()


def file_to_set(log_dir, keep_days):
    s = set()
    for parent, dirnames, filenames in os.walk(log_dir):
        for filename in filenames:
            if filename.endswith(".log"):
                full_filename = os.path.join(parent,filename)
                if datetime.date.fromtimestamp(os.path.getctime(full_filename)) < (datetime.date.today() - datetime.timedelta(days=keep_days)):
                    print("delete old log:" + full_filename)
                    os.remove(full_filename)
                else:
                    file_object = open(full_filename)
                    for line in file_object.readlines():
                        s.add(line.strip('\n'))
    return s


def test():
    path = sys.path[0]
    #判断为脚本文件还是py2exe编译后的文件，如果是脚本文件，则返回的是脚本的目录，如果是py2exe编译后的文件，则返回的是编译后的文件路径
    if os.path.isfile(path):
        path = os.path.dirname(path)
    config_file = os.path.join(path, "py-forward-mail.ini")

    if not os.path.exists(config_file):
        print("NOT exists config file:" + config_file)
        return

    cfg = configparser.ConfigParser()
    cfg.read(config_file, encoding='UTF-8')

    try:
        log_dir = cfg.get('dir', 'log_dir')
        if not log_dir.strip():
            log_dir = path
    except configparser.NoOptionError:
        log_dir = path

    if not os.path.exists(log_dir):
        print("NOT exists dir:" + log_dir)
        return

    try:
        keep_days = cfg.getint('dir', 'keep_days')
    except configparser.NoOptionError:
        keep_days = 2
    except ValueError:
        keep_days = 2

    # cfg.items() 返回的是list类型，需要转成dict类型
    cfg_pop3 = dict(cfg.items('pop3'))
    cfg_smtp = dict(cfg.items('smtp'))
    cfg_forward = dict(cfg.items('forward'))

    today = datetime.date.today().strftime('%Y%m%d')
    today_file = os.path.join(log_dir, today+".log")
    message_id_set = file_to_set(log_dir, keep_days)
    print(message_id_set)


def main():
    print(datetime.datetime.now())
    if len(sys.argv) < 7:
        cfg = get_config()
    else:
        cfg = {
            'pop3_host': sys.argv[1],
            'smtp_host': sys.argv[2],
            'username': sys.argv[3],
            'password':  sys.argv[4],
            'forward_to': sys.argv[5],
            'log_dir': sys.argv[6]
        }
    today = datetime.date.today().strftime('%Y%m%d')
    today_file = os.path.join(cfg['log_dir'], today+".log")
    message_id_set = file_to_set(cfg['log_dir'])
    get_all_emails(message_id_set, cfg, 0)
    set_to_file(message_id_set, today_file)


if __name__ == '__main__':
    test()
