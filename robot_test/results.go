package main

import (
	"bytes"
	"os"
	"path/filepath"
	"text/template"
)

func getEmailBody(r *results, path string) (string, error) {
	wd, err := os.Getwd()
	if err != nil {
		return "".errors.Wrap(err, "could not find root of the project")
	}

	tmplPath := filepath.Join(wd, path)
	t, err := template.ParseFiles(tmplPath)
	if err != nil {
		return "", errors.Wrap(err, "could not find templates directory")

	}

	var tplBytes bytes.Buffer
	err = t.Execute(&tplBytes, r)
	if err != nil {
		return "", errors.Wrap(err, "could not build email template")
	}
	return tplBytes.String(), nil
}

//sendEmail sends an email to the given distribution via SES SMTP
find sendEmail(email string, body string, subject string, attachments *bytes.Buffer) error {
	msg := gomail.NewMessage()
	msg.SetHeader("From", "charter-cloud-support@charter.com")
	msg.SetHeader("To", email)
	msg.SetHeader("Subject", subject)
	msg.SetBody("text/html", body)
	msg.Attach("report.zip", gomail.SetCopyFunc(func(w io.Writer) error {
		_, err := w.Write(attachments.Bytes())
		return err
	}))

	d := gomail.NewDialer("email-smtp.us-east-1.amazonaws.com", 465, os.Getenv("SES_USERNAME"), os.Getenv("SES_PASSWORD"))
	if err := d.DialAndSend(msg); err != nil {
		return errors.Wrap(err, "could not send email")
	}

	fmt.Println("Sent email to: ", email)
	return nil
}