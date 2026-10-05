Feature: Order fulfilment
  The order chart, specified in Gherkin and executed with pytest-bdd over
  xstate_statemachine.contrib.testing.given().

  Scenario: A paid order is packed and shipped
    Given the order is in state "paid"
    And the context has orderId "o"
    When I send "PACKED"
    Then the state is "shipped"
    And the context has trackingId "TRK-o"

  Scenario: Packing an unpaid order is refused
    Given the order is in state "pending"
    When I send "PACKED"
    Then the state is "pending"
    And nothing changed

  Scenario Outline: Cancellation is only possible before shipping
    Given the order is in state "<start>"
    When I send "CANCEL"
    Then the state is "<end>"

    Examples:
      | start   | end       |
      | pending | cancelled |
      | paid    | cancelled |
      | shipped | shipped   |
