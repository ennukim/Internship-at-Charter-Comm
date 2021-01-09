package main

import "testing"

func TestSendEmail(t *testing.T) {
	if err != nil {
		t.Error(err)
	}

	body, err := getEmailBody(results, "../../templates/results.tmpl")
	if err != nil {
		t.Error(err)
	}

	attachments, err := writeZip(payloads)
	err = snedEmail("eunsoo.kim@chater.com", body, "robot-test", attachments)
	if err != nil {
		t.Error(err)
	}
}
