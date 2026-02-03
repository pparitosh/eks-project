{{/*
Expand the name of the chart.
*/}}
{{- define "node-refresh-operator.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end }}
