// Template for an AWS_IAM Gateway. Substitute the stable principal ID and exact
// action names from the Gateway's generated policy schema before validation.
// This is NOT a deployed or service-validated policy. Unmatched actions deny.
permit (
  principal == AgentCore::IamEntity::"arn:aws:sts::${ACCOUNT_ID}:assumed-role/${HARNESS_ROLE_NAME}",
  action in [
    AgentCore::Action::"managed-kb___Retrieve",
    AgentCore::Action::"operations___get_ticket",
    AgentCore::Action::"operations___prepare_ticket_update"
  ],
  resource == AgentCore::Gateway::"${GATEWAY_ARN}"
);
